from __future__ import annotations

import sys
import queue as Q

from logging import getLogger
from typing import Generic, ClassVar, Tuple

from matplotlib import patches
from sortedcontainers import SortedKeyList

from ..agent import Agent
from ..util.intervals import UnsafeInterval, SafeInterval
from ..util.types import EdgeType, NodeType

logger = getLogger('__main__.' + __name__)


class IntervalStore(object):
    """Definition of a safe interval."""
    def __init__(self):
        super().__init__()
        self.unsafe_intervals: SortedKeyList = SortedKeyList(key=lambda x: x.start)
        self.safe_intervals: list[SafeInterval] = []
        self.bt: dict[int, float] = {}
        self.crt: dict[int, float] = {}
        self.merged = False

    def add_unsafe_interval(self, interval: UnsafeInterval):
        self.unsafe_intervals.add(interval)
        self.merged = False

    def remove_unsafe_interval(self, interval: UnsafeInterval):
        """Remove the unsafe interval from this node/edge. Will split the existing unsafe intervals to remove only the given interval. Assumes self.unsafe_intervals are merged.
        :param interval: Unsafe interval to remove.
        """
        assert self.merged
        self.merged = False

        uis = SortedKeyList(self.unsafe_intervals, key=lambda x: (x.by_agent.id, x.start))
        if len(uis) == 0:
            return
        index = uis.bisect_left(interval) - 1
        interval_left = uis[index] if index > 0 else None
        interval_right = uis[index + 1] if index < len(uis)-1 else None
        if interval_left and interval_left & interval and interval_left.by_agent == interval.by_agent:
            # Interval_left has a start earlier than interval, can overlap in two ways: encompassing the whole interval or only a part.
            self.unsafe_intervals.remove(interval_left)
            if interval_left.start < interval.start:
                new_ui = UnsafeInterval(interval_left.start, interval.start, interval_left.duration, interval_left.by_agent, interval_left.local_recovery_time)
                self.unsafe_intervals.add(new_ui)
            if interval_left.end > interval.end:
                new_ui = UnsafeInterval(interval.end, interval_left.end, interval_left.duration, interval_left.by_agent, interval_left.local_recovery_time)
                self.unsafe_intervals.add(new_ui)

        if interval_right and interval_right & interval and interval_right.by_agent == interval.by_agent:
            self.unsafe_intervals.remove(interval_right)
            if interval_right.start < interval.start:
                new_ui = UnsafeInterval(interval_right.start, interval.start, interval_right.duration, interval_right.by_agent, interval_right.local_recovery_time)
                self.unsafe_intervals.add(new_ui)
            if interval_right.end > interval.end:
                new_ui = UnsafeInterval(interval.end, interval_right.end, interval_right.duration, interval_right.by_agent, interval_right.local_recovery_time)
                self.unsafe_intervals.add(new_ui)

        assert interval not in self.unsafe_intervals

    def merge_unsafe_intervals(self):
        self.merged = True
        if len(self.unsafe_intervals) == 0:
            return
        unmerged_intervals = SortedKeyList(self.unsafe_intervals, key=lambda x: (x.by_agent.id, x.start))
        merged_intervals = SortedKeyList(key=lambda x: x.start)
        start = unmerged_intervals[0]
        for next in unmerged_intervals[1:]:
            # Check for overlap using intersection
            if start.by_agent == next.by_agent:
                if not (start & next):
                    logger.error(f"Merged non overlapping interval {start} and {next}")
                start = start | next
            else:
                merged_intervals.add(start)
                start = next
        merged_intervals.add(start)
        self.unsafe_intervals = merged_intervals

    def filter_out_agent(self, agent: Agent):
        self.unsafe_intervals = SortedKeyList([ui for ui in self.unsafe_intervals if ui.by_agent != agent], key=lambda x: x.start)
        self.merge_unsafe_intervals()

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
            if start == 0:
                agent_before = agent
                current = end
            else:
                bt_b, crt_b = self.get_flexibility(agent_before)
                bt_a, crt_a = self.get_flexibility(agent)
                interval = SafeInterval(current, start, agent_before, crt_b, agent, bt_a, crt_a)
                if current < start + bt_a:
                    # Dictionary with node keys, each entry has a dictionary with interval keys and then the index value
                    self.safe_intervals.append(interval)
                else:
                    logger.warning(f"INTERVAL WARNING: interval {interval} is empty on node {self} as start equals end of previous and there is no buffer time")
                agent_before = agent
                current = end
        if current < global_end_time:
            bt_b, crt_b = self.get_flexibility(agent_before)
            last_interval = SafeInterval(current, global_end_time, agent_before, crt_b, 0, 0, 0)
            self.safe_intervals.append(last_interval)

    def plot_unsafe_interval(self, ax, x1, x2, **kwargs):
        continues = kwargs.get("continues", False)
        for ui in self.unsafe_intervals:
            c = kwargs.get("bt_color", "lightblue")
            bt, _ = self.get_flexibility(ui.by_agent)

            if not continues:
                blocking_time = patches.Rectangle((x1, ui.start), x2 - x1, ui.end - ui.start,
                                                    linewidth=1, edgecolor=kwargs.get("edgecolor", "red"),
                                                    facecolor="none")
                buffer_time = patches.Rectangle((x1, ui.end), x2 - x1, bt,
                                                    linewidth=1, edgecolor=c, facecolor=c, alpha=0.5)
            else:
                x = [x1, x1, x2, x2]
                # x = [x2, x2, x1, x1]
                y = [ui.start, ui.end, ui.end + (x2 - x1), ui.start + (x2 - x1)]
                blocking_time = patches.Polygon(xy=list(zip(x,y)),
                                                linewidth=1, edgecolor=kwargs.get("edgecolor", "red"),
                                                facecolor="none")
                x = [x1, x1, x2, x2]
                y = [ui.end, ui.end + bt, ui.end + bt + (x2 - x1), ui.end + (x2 - x1)]
                buffer_time = patches.Polygon(xy=list(zip(x,y)),
                                              linewidth=1, edgecolor=c, facecolor=c, alpha=0.5)

            ax.add_patch(blocking_time)
            if kwargs.get("show_buffer_time", True):
                ax.add_patch(buffer_time)


class Node(IntervalStore, Generic[EdgeType, NodeType]):
    """Nodes in the @SIPP graphs, which are locations and a safe interval, with incoming and outgoing ATF edges."""
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
                sorted_inc = sorted(current.incoming, key=lambda x: x.length)
                for x in sorted_inc:
                    if x.from_node == previous[current.name]:
                        path.insert(0, x)
                        break
                current = previous[current.name]
        else:
            logger.error(f"##### ERROR ### No path was found between {self.name} and {to.name}")
        return path

    def get_safe_connections(self, allowed_nodes: set[NodeType], allowed_edges: set[EdgeType]) -> list[
        Tuple[SafeInterval, SafeInterval, SafeInterval, float]]:
        safe_connections = []

        def check_interval_overlap(l: SafeInterval, r: SafeInterval) -> bool:
            return bool((l + from_interval.buffer_after) & (r + r.buffer_after))

        def check_interval_agent(l: SafeInterval, r: SafeInterval) -> bool:
            if (l.agent_before == 0 and r.agent_after == 0) and (l.agent_after == 0 and r.agent_before == 0):
                return True
            if l.agent_before == 0 and r.agent_after == 0:
                return l.agent_after != r.agent_before
            if l.agent_after == 0 and r.agent_before == 0:
                return l.agent_before != r.agent_after
            return (l.agent_before != r.agent_after) and (
                    l.agent_after != r.agent_before)

        for from_interval in self.safe_intervals:
            for edge in self.outgoing:
                if edge in allowed_edges and edge.to_node in allowed_nodes:
                    for edge_interval in edge.safe_intervals:
                        if check_interval_agent(from_interval, edge_interval) & check_interval_overlap(from_interval, edge_interval):
                            for to_interval in edge.to_node.safe_intervals:
                                if check_interval_agent(edge_interval, to_interval) & check_interval_overlap(edge_interval, to_interval):
                                    safe_connections.append((from_interval, edge_interval, to_interval, edge))
        return safe_connections

    def append_label(self, labels:list[tuple[int, str]], x: int):
        labels.append((x, self.name))


class Edge(IntervalStore, Generic[EdgeType, NodeType]):
    """Edge in the @SIPP graph is an ATF describing safe traversal from the from_node to the to_node."""
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
            return self.id == other.id
        return False

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(self.id)

    def __str__(self):
        return f"{self.from_node.name}--{self.to_node.name}"


class Graph(Generic[EdgeType, NodeType]):
    """@SIPP graph with ATFs as edges and (configuration, safe-interval) pairs as nodes."""
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
            ui.safe_intervals.clear()
            ui.get_safe_intervals(self.global_end_time)

    def reset_flexibility(self):
        uis: list[IntervalStore] = list(self.nodes.values()) + self.edges
        for ui in uis:
            ui.crt = {}
            ui.bt = {}

    def calculate_heuristic(self, start: NodeType) -> dict[str, float]:
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
                tmp = time_distances[v.name] + (e.length / e.max_speed)
                if tmp < time_distances[e.from_node.name]:
                    time_distances[e.from_node.name] = tmp
                    pq.put((time_distances[e.from_node.name], pq_counter, e.from_node))
                    pq_counter += 1
                    logger.debug(f"time-distance to {e.from_node.name}: {tmp}")
        return time_distances

    def distance_between_nodes(self, start: NodeType, end: NodeType, agent_velocity):
        if start is None or end is None:
            return sys.maxsize
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
                sorted_inc = sorted(current.incoming, key=lambda x: x.length)
                for x in sorted_inc:
                    if x.from_node == previous[current.name]:
                        path.insert(0, x)
                        break
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

    def _update_delayed_agent(self, *args, **kwargs):
        # This is more implementation specific, should be overwritten if used
        raise NotImplementedError

    def _update_using_minimum_delays(self, minimum_delays):
        for agent, delays in minimum_delays.items():
            if delays:
                current_delay = 0
                new_unsafe_intervals: list[tuple[IntervalStore, UnsafeInterval, UnsafeInterval]] = []
                for move in agent.route:
                    filtered_uis = [ui for ui in move.unsafe_intervals if ui.by_agent == agent]
                    if len(filtered_uis)>0:
                        ui = filtered_uis[0]
                        new_delay = delays.get(move, 0)
                        if current_delay < new_delay:
                            # Delay becomes larger, thus the agent should wait here. Extend end of interval delay, start of interval is shifted by old delay
                            # As it's standing still here (at this node), it is gaining local recovery time by the difference in delay amount
                            new_ui = UnsafeInterval(ui.start + current_delay, ui.end + new_delay, ui.local_recovery_time + new_delay - current_delay, ui.by_agent, ui.local_recovery_time + new_delay - current_delay)
                            current_delay = new_delay
                        else:
                            recovery_used = min(ui.local_recovery_time, current_delay)
                            updated_delay = current_delay - recovery_used
                            new_ui = UnsafeInterval(ui.start + current_delay, ui.end + updated_delay, ui.duration - recovery_used, ui.by_agent, ui.local_recovery_time - recovery_used)
                            current_delay = updated_delay
                        new_unsafe_intervals.append((move, ui, new_ui))
                for move, old_ui, new_ui in new_unsafe_intervals:
                    move.remove_unsafe_interval(old_ui)
                    move.add_unsafe_interval(new_ui)
                    move.merge_unsafe_intervals()

    def update_unsafe_intervals(self, new_path=None, minimum_delays=None):
        if new_path is not None:
            self._update_delayed_agent(*new_path)
        if minimum_delays is not None:
            self._update_using_minimum_delays(minimum_delays)

    def filter_out_agent(self, agent: Agent):
        uis:list[IntervalStore] = list(self.nodes.values()) + self.edges
        for ui in uis:
            ui.filter_out_agent(agent)
