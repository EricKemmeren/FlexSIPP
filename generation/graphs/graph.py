from __future__ import annotations

import sys
from enum import Enum

import queue as Q

from logging import getLogger

from generation.util.intervals import UnsafeInterval, SafeInterval

logger = getLogger('__main__.' + __name__)

class Direction(Enum):
    SAME = 1
    OPPOSE = 2
    BOTH = 3

class Node:
    def __init__(self, name: str):
        self.name = name
        self.outgoing:list[Edge] = []
        self.incoming:list[Edge] = []
        self.unsafe_intervals: list[UnsafeInterval] = []
        self.safe_intervals: list[SafeInterval] = []

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

    def calculate_path(self, to: Node):
        distances = {self.name: 0.0}
        previous: dict[str, Node] = {}

        found = False
        pq = Q.PriorityQueue()
        pq.put((distances[self.name], self))
        while not pq.empty() and not found:
            u: Node = pq.get()[1]
            for e in u.outgoing:
                v = e.to_node
                distance = distances[u.name] + e.length
                if not v.name in distances or distance < distances[v.name]:
                    distances[v.name] = distance
                    previous[v.name] = u
                    if v == to:
                        found = True
                        break
                    pq.put((distances[v.name], v))

        path: list[Edge] = []
        current = previous[to.name]
        if found:
            while current != self:
                for x in current.incoming:
                    if x.from_node == previous[current.name]:
                        path.insert(0, x)
                current = previous[current.name]
        else:
            logger.error(f"##### ERROR ### No path was found between {self.name} and {to.name}")
        return path


    # TODO: insertion sort on start of interval, and maybe merge overlapping intervals
    def add_unsafe_interval(self, interval: UnsafeInterval):
        self.unsafe_intervals.append(interval)

    def get_safe_intervals(self, index, buffer_times, global_end_time):
        current = 0
        train_before = 0
        # Make sure they are ordered in chronological order
        self.unsafe_intervals.sort()
        # Each tuple is (start, end, duration, train)
        for start, end, dur, train, _ in self.unsafe_intervals:
            if current > start:
                buffer_after = buffer_times[train][self] if self in buffer_times[train] else 0
                interval = (current, start, train_before, train, buffer_after, 0)
                train_before = train
                logger.error(
                    f"INTERVAL ERROR safe node interval {interval} on node {self} has later end than start.")
            elif current == start:
                # Don't add safe intervals like (0,0), but do update for the next interval
                logger.error(f"INTERVAL ERROR current == end.")
                train_before = train
                current = end
            else:
                buffer_after = buffer_times[train][self] if self in buffer_times[train] else 0
                interval = SafeInterval(current, start, train_before, train, buffer_after, 0)
                train_before = train
                current = end
                # Dictionary with node keys, each entry has a dictionary with interval keys and then the index value
                self.safe_intervals.append(interval)
                index += 1
        if current < global_end_time:
            last_interval = SafeInterval(current, global_end_time, train_before, 0, 0, 0)
            self.safe_intervals.append(last_interval)
            index += 1
        return index

    def apply_to_safe_connections(self, func):
        assert len(self.safe_intervals) > 0
        for from_interval in self.safe_intervals:
            for edge in self.outgoing:
                for edge_interval in edge.safe_intervals:
                    # Check for overlap with the from node and edge
                    if from_interval & edge_interval:
                        for to_interval in edge.to_node.safe_intervals:
                            # Check for overlap with the edge en to node
                            # TODO: figure out if overlap with from and to node is needed
                            if edge_interval & to_interval:
                                func(from_interval, edge_interval, to_interval, edge.length)


class Signal:
    def __init__(self, id, track: Node):
        self.id = id
        self.track = track
        self.direction = track.direction

    def __repr__(self) -> str:
        return f"Signal {self.id} on track {self.track}"


class Edge:
    __last_id = 1
    def __init__(self, f:Node, t:Node, l:float, mv:float):
        self.id = Edge.__last_id
        Edge.__last_id += 1
        self.from_node = f
        self.to_node = t
        self.length = l
        self.max_speed = mv
        self.unsafe_intervals: list[UnsafeInterval] = []
        self.safe_intervals: list[SafeInterval] = []

    def get_identifier(self):
        return f"{self.from_node.name}--{self.to_node.name}--{self.id}"

    def __repr__(self) -> str:
        return f"Edge from {self.from_node.name} to {self.to_node.name} with length {self.length}"

    def __eq__(self, other):
        if isinstance(other, Edge):
            return self.from_node == other.from_node and self.to_node == other.to_node
        return False

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(self.id)

    def __str__(self):
        return f"{self.from_node.name}--{self.to_node.name}"

    # TODO: insertion sort on start of interval, and maybe merge overlapping intervals
    def add_unsafe_interval(self, interval: UnsafeInterval):
        self.unsafe_intervals.append(interval)

    def get_safe_intervals(self, index, global_end_time):
        state_indices = {}

        current = 0
        train_before = 0
        dur_before = 0
        # Make sure they are ordered in chronological order
        self.unsafe_intervals.sort()
        # Each tuple is (start, end, duration)
        for start, end, dur, train, _ in self.unsafe_intervals:
            if current > start:
                interval = SafeInterval(current, start, train_before, train, dur_before, end - start)
                train_before = train
                dur_before = end - start
                logger.info(
                    f"INTERVAL ERROR safe edge interval {interval} on edge {self} has later end than start.")
            elif current == start:
                # Don't add safe intervals like (0,0), but do update for the next interval
                logger.error(f"INTERVAL ERROR current == end.")
                train_before = train
                dur_before = end - start
                current = end
            else:
                # Create safe interval from the end of the last unsafe interval, to the start of the next unsafe interval
                interval = SafeInterval(current, start, train_before, train, dur_before, end - start)
                train_before = train
                dur_before = end - start
                self.safe_intervals.append(interval)
                index += 1
                current = end
        if current < global_end_time:
            # The current timestep is still before the end time of the simulation, thus there is a safe interval from now till the end
            last_interval = SafeInterval(current, global_end_time, train_before, 0, dur_before, 0)
            self.safe_intervals.append(last_interval)
            index += 1
        return index

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

    def invert_unsafe_intervals(self, buffer_times):
        """
            Creates safe intervals by inverting the unsafe intervals of all the nodes and edges in the graph.
        """
        index = 0
        for name, node in self.nodes:
            index = node.get_safe_intervals(index, buffer_times, self.global_end_time)
            index += index

        for edge in self.edges:
            index = edge.get_safe_intervals(index, self.global_end_time)
            index += index

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

    def calculate_path(self, start: Node, end: Node):
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