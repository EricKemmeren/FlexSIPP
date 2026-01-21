from __future__ import annotations

import re
import logging
import sys
from enum import Enum

import tqdm
import queue as Q

from queue import Queue
from copy import copy
from logging import getLogger

a_to_s = {
    "4.5": 40,
    "7": 40,
    "8": 40,
    "9": 40,
    "10": 40,
    "12": 60,
    "15": 80,
    "18": 80,
    "18.5": 80,
    "20": 125,
    "29": 140,
    "34.7": 140,
    "39.1": 160
}
def angle_to_speed(angle):
    if angle is None:
        return 200 / 3.6
    return a_to_s[angle] / 3.6

logger = getLogger('__main__.' + __name__)

class Direction(Enum):
    SAME = 1
    OPPOSE = 2
    BOTH = 3

class TqdmLogger:
    """File-like class redirecting tqdm progress bar to given logging logger."""
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def write(self, msg: str) -> None:
        self.logger.info(msg.lstrip("\r"))

    def flush(self) -> None:
        pass

class Node:
    def __init__(self, name):
        self.name = name
        self.outgoing:list[Edge] = []
        self.incoming:list[Edge] = []

    def get_identifier(self):
        return f"{self.name}"

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.name == other.name
        return False

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(self.name)

    def __repr__(self) -> str:
        # return f"Node {self.name} of type {self.type} coming from {self.incoming} and going to {self.outgoing}\n"
        return f"Node {self.name}"

    def __str__(self) -> str:
        # return f"Node {self.name} of type {self.type} coming from {self.incoming} and going to {self.outgoing}\n"
        return f"{self.name}"

class BlockNode(Node):
    def __init__(self, name, readable_name=None):
        super().__init__(name)
        self.readable_name = readable_name

    def get_identifier(self):
        if self.readable_name is None:
            return super().get_identifier()
        return self.readable_name
    
    def __repr__(self):
        if self.readable_name is None:
            return super().__repr__()
        return self.readable_name
    
    def __str__(self):
        if self.readable_name is None:
            return super().__str__()
        return self.readable_name

class TrackNode(Node):
    def __init__(self, name, type):
        super().__init__(name)
        self.associated:list[Node] = []
        self.opposites:list[Node] = []
        self.blk:list[BlockEdge] = []
        self.blocksOpp:list[BlockEdge] = []
        self.canReverse = False
        self.stationPlatform = False
        self.type = type
        self.direction = ''.join(set(re.findall("[AB]", f"{name[-2:]}")))
        if self.direction != "A" and self.direction != "B":
            raise ValueError("Direction must be either A or B")

    def blocks(self, dir=Direction.SAME):
        if dir == Direction.SAME:
            return self.blk
        if dir == Direction.OPPOSE:
            return self.blocksOpp
        return self.blk + self.blocksOpp

class Signal:
    def __init__(self, id, track: TrackNode):
        self.id = id
        self.track = track
        self.direction = track.direction

    def __repr__(self) -> str:
        return f"Signal {self.id} on track {self.track}"


class Edge:
    __last_id = 1
    def __init__(self, f:Node, t:Node, l, mv):
        self.id = Edge.__last_id
        Edge.__last_id += 1
        self.from_node = f
        self.to_node = t
        self.length = l
        self.max_speed = mv

    def get_identifier(self):
        return f"{self.from_node.name}--{self.to_node.name}--{self.id}"

    def __repr__(self) -> str:
        return f"Edge from {self.from_node} to {self.to_node} with length {self.length}"

    def __eq__(self, other):
        if isinstance(other, Edge):
            return self.from_node == other.from_node and self.to_node == other.to_node
        return False

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(self.id)

    def __str__(self):
        return f"{self.from_node.name}--{self.to_node.name}"

class BlockEdge(Edge):
    def __init__(self, f, t, l, tracknodes_on_route:list[TrackNode], direction, mv):
        super().__init__(f, t, l, mv)
        self.tn:list[TrackNode] = list(tracknodes_on_route)
        self.tnAssociated:list[TrackNode] = list()
        self.tnOpposites:list[TrackNode] = list()
        for n in tracknodes_on_route:
            self.tnAssociated.extend(n.associated)
            self.tnOpposites.extend(n.opposites)
        self.direction = direction
        if self.direction == "BA":
            self.direction = "AB"

    def tracknodes(self, direction:Direction) -> list[TrackNode]:
        if direction == Direction.BOTH:
            return self.tn + self.tnAssociated + self.tnOpposites
        if direction == Direction.SAME:
            return self.tn + self.tnAssociated
        return self.tnOpposites


    def get_affected_blocks(self) -> list:
        affected_blocks = set()
        for node in self.tracknodes(Direction.BOTH):
            affected_blocks = affected_blocks.union(set(node.blocks(Direction.BOTH)))
        return list(affected_blocks)


class TrackEdge(Edge):
    def __init__(self, f, t, l, switch_angle=None):
        super().__init__(f, t, l, angle_to_speed(switch_angle))
        self.plotting_info = {}
        self.opposites:  list[Edge] = []
        self.associated: list[Edge] = []
        self.stops_at_station = {}
        self.direction = ''.join(set(re.findall("[AB]", f"{str(f)[-2:]} {str(t)[-2:]}")))
        # if self.direction != "A" and self.direction != "B":
        #     raise ValueError("Direction must be either A or B")


    def set_plotting_info(self, agent, cur_time, end_time, block_edge):
        self.plotting_info[agent] = {
            "start_time": cur_time,
            "end_time": end_time,
            "block": block_edge,
        }


class Graph:
    def __init__(self):
        self.edges: list[Edge] = []
        self.nodes: dict[str, Node] = {}
        self.global_end_time = -1
        self.stations: dict[str, (str, str)] = {}

    def add_node(self, n):
        if isinstance(n, Node):
            self.nodes[n.name] = n
            return n

    def add_edge(self, e):
        if isinstance(e, Edge):
            self.edges.append(e)
            e.to_node.incoming.append(e)
            e.from_node.outgoing.append(e)
            return e

    def __repr__(self) -> str:
        return f"Graph with {len(self.edges)} edges and {len(self.nodes)} nodes:\n{self.nodes.values()}"

    def __eq__(self, other):
        if isinstance(other, Graph):
            return (self.edges == other.edges and
                    self.nodes == other.nodes and
                    self.global_end_time == other.global_end_time)
        return NotImplemented

    def get_station(self, station):
        if station in self.stations:
            return self.stations[station]
        if f"{station}a" in self.stations:
            return self.stations[f"{station}a"]
        if f"{station}b" in self.stations:
            return self.stations[f"{station}b"]
        if station[0:-1] in self.stations:
            return self.stations[station[0:-1]]
        raise ValueError(f"{station} is not a station")

    def calculate_heuristic(self, start: Node, agent_velocity):
        time_distances = {n: sys.maxsize for n in self.nodes}
        pq = Q.PriorityQueue()
        time_distances[start.name] = 0
        pq_counter = 0
        # Use a counter so it doesn't have to compare nodes
        pq.put((time_distances[start.name], pq_counter, start))
        pq_counter += 1
        # This does not include the other node intervals: this will have to be updated with propagating SIPP searches
        while not pq.empty():
            v = pq.get()[2]
            for e in v.incoming:
                velocity = min(e.max_speed, agent_velocity)
                tmp = time_distances[v.name] + (e.length / velocity)
                if tmp < time_distances[e.from_node.name]:
                    time_distances[e.from_node.name] = tmp
                    pq.put((time_distances[e.from_node.name], pq_counter, e.from_node))
                    pq_counter += 1
                    logger.debug(f"time-distance to {e.from_node.name}: {tmp}")
        return time_distances

    def distance_between_nodes(self, start: Node, end: Node, agent_velocity):
        time_distances = {n: sys.maxsize for n in self.nodes}
        pq = Q.PriorityQueue()
        time_distances[start.name] = 0
        pq_counter = 0
        # Use a counter so it doesn't have to compare nodes
        pq.put((time_distances[start.name], pq_counter, start))
        pq_counter += 1
        # This does not include the other node intervals: this will have to be updated with propagating SIPP searches
        while not pq.empty():
            u = pq.get()[2]
            for e in u.outgoing:
                velocity = min(e.max_speed, agent_velocity)
                tmp = time_distances[u.name] + (e.length / velocity)
                v = e.to_node
                if tmp < time_distances[v.name]:
                    time_distances[v.name] = tmp
                    if end is not None and v.name == end.name:
                        return tmp
                    pq.put((time_distances[v.name], pq_counter, v))
                    pq_counter += 1
        return sys.maxsize

    def calculate_path(self, start, end):
        distances = {n: sys.maxsize for n in self.nodes}
        previous = {n: None for n in self.nodes}
        previous_edge = {n: None for n in self.nodes}
        pq = Q.PriorityQueue()
        distances[start.name] = 0
        pq_counter = 0
        # Use a counter so it doesn't have to compare nodes
        pq.put((distances[start.name], pq_counter, start))
        pq_counter += 1
        # This does not include the other node intervals: this will have to be updated with propagating SIPP searches
        while not pq.empty():
            u = pq.get()[2]
            for v in u.outgoing:
                tmp = distances[u.name] + v.length
                if tmp < distances[v.to_node.name]:
                    distances[v.to_node.name] = tmp
                    previous[v.to_node.name] = u
                    previous_edge[v.to_node.name] = v
                    pq.put((distances[v.to_node.name], pq_counter, v.to_node))
                    pq_counter += 1
        path = []
        current = end
        try:
            while current != start:
                for x in current.incoming:
                    if x.from_node == previous[current.name]:
                        path.insert(0, x)
                current = previous[current.name]
        except Exception as e:
            logger.error(f"##### ERROR ### {e} No path was found between {start.name} and {end.name}")
        return path

    def get_initial_direction(self, start, end, agent_velocity):
        start_a, start_b = start
        end_a, end_b = end
        start_a, start_b, end_a, end_b = self.nodes[start_a], self.nodes[start_b], self.nodes[end_a], self.nodes[end_b]
        length_aa = self.distance_between_nodes(start_a, end_a, agent_velocity)
        length_ab = self.distance_between_nodes(start_a, end_b, agent_velocity)
        length_ba = self.distance_between_nodes(start_b, end_a, agent_velocity)
        length_bb = self.distance_between_nodes(start_b, end_b, agent_velocity)
        logger.debug(f"Shortest distance side: aa: {length_aa}, ab: {length_ab}, ba: {length_ba}, bb: {length_bb}")
        min_length = min(length_aa, length_ab, length_ba, length_bb)
        if min_length in [length_aa, length_ab]:
            return 0
        return 1

    def construct_path(self, move, print_path_error=True, current_agent=0, agent_velocity=15):
        """Construct a shortest path from the start to the end location to determine the locations and generate their unsafe intervals."""
        start = self.get_station(move["startLocation"])
        old_stops = move["stops"]
        departure_times = {}
        stops = []
        for stop in old_stops:
            location = self.get_station(stop["location"])
            time = stop["time"]
            stops.append(location)
            departure_times[location] = time
        end = self.get_station(move["endLocation"])
        all_movements = [start] + stops + [end]
        logger.debug(f"Finding path via {all_movements}")
        path = []
        direction = self.get_initial_direction(all_movements[0], all_movements[1], agent_velocity)
        for i in range(len(all_movements) - 1):
            start = self.nodes[all_movements[i][direction]]
            end_a = self.nodes[all_movements[i + 1][0]]
            end_b = self.nodes[all_movements[i + 1][1]]
            dist_a = self.distance_between_nodes(start, end_a, agent_velocity)
            dist_b = self.distance_between_nodes(start, end_b, agent_velocity)
            if dist_a <= dist_b:
                next_path = self.calculate_path(start, end_a)
                direction = 0
            else:
                next_path = self.calculate_path(start, end_b)
                direction = 1
            if next_path and i != 0:
                next_path[0].stops_at_station[current_agent] = departure_times[all_movements[i]]
            path.extend(next_path)

        return path

class TrackGraph(Graph):
    def __init__(self, file_name=None):
        super().__init__()
        self.signals: list[Signal] = []
        self.distance_markers = {}
        self.file_name = file_name

    def add_signal(self, s):
        if isinstance(s, Signal):
            self.signals.append(s)


class BlockGraph(Graph):
    def __init__(self, g: TrackGraph = None):
        super().__init__()
        if g == None:
            return
        logger.info("Creating initial signals")
        track_to_signal = {signal.track: signal for signal in g.signals}
        for signal in g.signals:
            block = self.add_node(BlockNode(f"r-{signal.id}"))
            signal.track.blk.append(block)
        for signal in tqdm.tqdm(g.signals, file=TqdmLogger(logger), mininterval=1, ascii=False):
            logger.debug(f"Expanding blocks of {signal}")
            blocks = self.generate_signal_blocks(signal, g.signals)
            for idx, (block, length, max_velocity) in enumerate(blocks):

                # Create edges in g_block
                from_signal_node = self.nodes[f"r-{signal.id}"]

                # Only add edge if a signal is found at the end of the route
                to_signal = track_to_signal[block[-1]]
                to_signal_node = self.nodes[f"r-{to_signal.id}"]
                direction = "".join(set(signal.direction + to_signal.direction))
                e = self.add_edge(BlockEdge(from_signal_node, to_signal_node, length, block, direction, max_velocity))
                logger.debug(f"Found block {e} with length {length} and max velocity {max_velocity}")
        for station, track_nodes in g.stations.items():
            node_a, node_b = track_nodes

            station_track_a = g.nodes[node_a]
            station_block_a = {edge.to_node.name for edge in station_track_a.blocks(Direction.SAME) if
                               isinstance(edge, BlockEdge) and station_track_a.direction in edge.direction}
            if len(station_block_a) == 0:
                logger.error(f"Found no blocks corresponding to track {station_track_a}")
                continue

            station_track_b = g.nodes[node_b]
            station_block_b = {edge.to_node.name for edge in station_track_b.blocks(Direction.SAME) if
                               isinstance(edge, BlockEdge) and station_track_b.direction in edge.direction}
            if len(station_block_b) == 0:
                logger.error(f"Found no blocks corresponding to track {station_block_b}")
                continue

            self.stations[station] = (station_block_a.pop(), station_block_b.pop())

    def __eq__(self, other):
        return super().__eq__(other)

    def add_edge(self, e):
        super().add_edge(e)

        for node in e.tracknodes(Direction.SAME):
            node.blk.append(e)
        for node in e.tracknodes(Direction.OPPOSE):
            node.blocksOpp.append(e)

        return e

    def generate_signal_blocks(self, from_signal: Signal, signals: list[Signal]):
        end_tracks = {s.track.get_identifier() for s in signals}
        start_track = from_signal.track

        result = []

        queue = Queue()
        queue.put(([start_track], {start_track}, 0, sys.maxsize))

        while not queue.empty():
            route, visited, length, max_velocity = queue.get()

            if len(route[-1].outgoing) == 0:
                #No outgoing edges, what to do?
                # Should only happen when at the end of a track, and it's not allowed to turn around
                logger.debug(f"No outgoing edges at {route[-1]}")
                continue

            for e in route[-1].outgoing:
                next_track = e.to_node

                if next_track.get_identifier() in end_tracks:
                    route = copy(route)
                    route.append(next_track)
                    result.append((route[1:], length + e.length, min(max_velocity, e.max_speed)))

                elif next_track not in visited:
                    route = copy(route)
                    visited = copy(visited)

                    visited.add(next_track)
                    route.append(next_track)
                    queue.put((route, visited, length + e.length, min(max_velocity, e.max_speed)))

        return result


def block_graph_constructor(g: TrackGraph):
    return BlockGraph(g)