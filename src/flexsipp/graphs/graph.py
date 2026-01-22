from __future__ import annotations

import sys
import queue as Q

from logging import getLogger
from typing import Generic, ClassVar, Tuple

from sortedcontainers import SortedKeyList

from ..agent import Agent
from ..util.intervals import UnsafeInterval, SafeInterval
from ..util.types import EdgeType, NodeType

logger = getLogger('__main__.' + __name__)


class IntervalStore(object):
    def __init__(self):
        super().__init__()
        self.unsafe_intervals: SortedKeyList[UnsafeInterval] = SortedKeyList(key=lambda x: x.start)
        self.safe_intervals: list[SafeInterval] = []
        self.bt: dict[int, float] = {}
        self.crt: dict[int, float] = {}
        self.merged = False

    def add_unsafe_interval(self, interval: UnsafeInterval):
        self.unsafe_intervals.add(interval)

    def merge_unsafe_intervals(self):
        self.merged = True
        if len(self.unsafe_intervals) == 0:
            return
        start = self.unsafe_intervals[0]
        for next in self.unsafe_intervals[1:]:
            # Check for overlap using intersection
            if start & next:
                start.merge(next)
                self.unsafe_intervals.remove(next)
            else:
                start = next

    def filter_out_agent(self, agent: Agent):
        return [ui for ui in self.unsafe_intervals if ui.by_agent.id != agent.id]


    def add_flexibility(self, agent: Agent, bt: float, crt:float):
        """
        Add the flexibility parameters to this node/edge
        @param agent: Agent for which the bt and crt are defined
        @param bt: Buffer Time at this node/edge
        @param crt: Compound Recovery Time at this node/edge
        """
        if agent.id in self.bt:
            self.bt[agent.id] = min(self.bt[agent.id], bt)
        else:
            self.bt[agent.id] = bt
        if agent.id in self.crt:
            self.crt[agent.id] = min(self.crt[agent.id], crt)
        else:
            self.crt[agent.id] = crt

    def get_flexibility(self, agent: Agent) -> Tuple[float, float]:
        if isinstance(agent, int):
            return 0, 0
        bt = self.bt[agent.id] if agent.id in self.bt else 0
        crt = self.crt[agent.id] if agent.id in self.crt else 0
        return bt, crt

    def get_safe_intervals(self, global_end_time):
        assert self.merged
        current = 0
        agent_before = 0
        # Each tuple is (start, end, duration, train, recovery_time)
        for start, end, dur, agent, recovery in self.unsafe_intervals:
            if current > start:
                bt_b, crt_b = self.get_flexibility(agent_before)
                bt_a, crt_a = self.get_flexibility(agent)
                interval = SafeInterval(current, start, agent_before, crt_b, agent, bt_a, crt_a)
                agent_before = agent
                logger.error(
                    f"INTERVAL ERROR safe node interval {interval} on node {self} has later end than start.")
            elif current == start:
                # Don't add safe intervals like (0,0), but do update for the next interval
                logger.error(f"INTERVAL ERROR current == end.")
                agent_before = agent
                current = end
            else:
                bt_b, crt_b = self.get_flexibility(agent_before)
                bt_a, crt_a = self.get_flexibility(agent)
                interval = SafeInterval(current, start, agent_before, crt_b, agent, bt_a, crt_a)
                agent_before = agent
                current = end
                # Dictionary with node keys, each entry has a dictionary with interval keys and then the index value
                self.safe_intervals.append(interval)
        if current < global_end_time:
            bt_b, crt_b = self.get_flexibility(agent_before)
            last_interval = SafeInterval(current, global_end_time, agent_before, crt_b, 0, 0, 0)
            self.safe_intervals.append(last_interval)


class Node(IntervalStore, Generic[EdgeType, NodeType]):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.outgoing:list[EdgeType] = []
        self.incoming:list[EdgeType] = []

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

    def __lt__(self, other):
        if isinstance(other, Node):
            return self.name < other.name

    def calculate_path(self, to: NodeType):
        distances = {self.name: 0.0}
        previous: dict[str, NodeType] = {}

        found = False
        pq = Q.PriorityQueue()
        pq.put((distances[self.name], self))
        while not pq.empty() and not found:
            u: NodeType = pq.get()[1]
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

        path: list[EdgeType] = []
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

    def get_safe_connections(self) -> list[Tuple[SafeInterval, SafeInterval, SafeInterval, float]]:
        assert len(self.safe_intervals) > 0
        safe_connections = []
        for from_interval in self.safe_intervals:
            for edge in self.outgoing:
                for edge_interval in edge.safe_intervals:
                    # Check for overlap with the from node and edge
                    if from_interval & edge_interval:
                        for to_interval in edge.to_node.safe_intervals:
                            # Check for overlap with the edge en to node
                            # TODO: figure out if overlap with from and to node is needed
                            if edge_interval & to_interval:
                                safe_connections.append((from_interval, edge_interval, to_interval, edge.length))
        return safe_connections


class Edge(IntervalStore, Generic[EdgeType, NodeType]):
    __last_id: ClassVar[int] = 1

    def __init__(self, f: NodeType, t: NodeType, l: float, mv: float):
        super().__init__()
        self.id = Edge.__last_id
        Edge.__last_id += 1
        self.from_node = f
        self.to_node = t
        self.length = l
        self.max_speed = mv

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


class Graph(Generic[EdgeType, NodeType]):
    def __init__(self):
        self.edges: list[EdgeType] = []
        self.nodes: dict[str, NodeType] = {}
        self.global_end_time = -1

    def add_node(self, n: NodeType) -> NodeType:
        if isinstance(n, Node):
            self.nodes[n.name] = n
        return n

    def add_edge(self, e: EdgeType) -> EdgeType:
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

    def invert_unsafe_intervals(self):
        """
            Creates safe intervals by inverting the unsafe intervals of all the nodes and edges in the graph.
        """
        uis: list[IntervalStore] = list(self.nodes.values()) + self.edges
        for ui in uis:
            ui.get_safe_intervals(self.global_end_time)

    def calculate_heuristic(self, start: NodeType, agent_velocity) -> dict[str, float]:
        time_distances = {n: float("inf") for n in self.nodes}
        pq = Q.PriorityQueue()
        time_distances[start.name] = 0.0
        pq_counter = 0
        # Use a counter so it doesn't have to compare nodes
        pq.put((time_distances[start.name], pq_counter, start))
        pq_counter += 1
        # This does not include the other node intervals: this will have to be updated with propagating SIPP searches
        while not pq.empty():
            v: NodeType = pq.get()[2]
            for e in v.incoming:
                velocity = min(e.max_speed, agent_velocity)
                tmp = time_distances[v.name] + (e.length / velocity)
                if tmp < time_distances[e.from_node.name]:
                    time_distances[e.from_node.name] = tmp
                    pq.put((time_distances[e.from_node.name], pq_counter, e.from_node))
                    pq_counter += 1
                    logger.debug(f"time-distance to {e.from_node.name}: {tmp}")
        return time_distances

    def distance_between_nodes(self, start: NodeType, end: NodeType, agent_velocity):
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

    def calculate_path(self, start: NodeType, end: NodeType) -> list[EdgeType]:
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

if __name__ == '__main__':
    n = Node("test")
    n.add_unsafe_interval(UnsafeInterval(2, 5, 1, 0, 1))
    n.add_unsafe_interval(UnsafeInterval(10, 15, 2, 0, 1))
    n.add_unsafe_interval(UnsafeInterval(0, 6, 4, 0, 1))
    n.add_unsafe_interval(UnsafeInterval(12, 20, 8, 0, 1))
    n.add_unsafe_interval(UnsafeInterval(18, 25, 16, 0, 1))
    n.add_unsafe_interval(UnsafeInterval(-5, 0, 32, 0, 1))

    for i in n.unsafe_intervals:
        print(i, i.local_recovery_time)

    print ("MERGING")
    n.merge_unsafe_intervals()

    for i in n.unsafe_intervals:
        print(i, i.local_recovery_time)