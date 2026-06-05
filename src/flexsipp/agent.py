import logging
from typing import Generic

from matplotlib.axis import Axis

from .util.types import EdgeType, NodeType

logger = logging.getLogger('__main__.' + __name__)

class Agent(Generic[EdgeType, NodeType]):

    def __init__(self, id:int, route: list[EdgeType | NodeType]):
        """ Create an agent with the given id and route.

        :param int id: Numeric id of the agent.
        :param list route: Ordered list of nodes and or edges in order that the agent passes
        """
        self.id = id
        self.route: list[EdgeType | NodeType] = route
        self.max_buffer = float("inf")

    @staticmethod
    def calculate_route(start: NodeType, stops: list[NodeType], **kwargs):
        """ Calculate a route from the start node to every stop in stops, assumes that the nodes have implemented a calculate_path function.

        :param NodeType start: Starting node.
        :param list[NodeType] stops: List of stops.
        :return: Edges of the shortest path.
        """
        route: list[EdgeType] = []
        previous_stop = start

        for next_stop in stops:
            route += (previous_stop.calculate_path(next_stop))
            previous_stop = next_stop

        return route

    @property
    def origin(self) -> NodeType:
        try:
            return self.route[0].from_node
        except AttributeError:
            return self.route[0]

    @property
    def destination(self) -> NodeType:
        try:
            return self.route[-1].to_node
        except AttributeError:
            return self.route[-1]

    def _get_local_flexibility(self, move: EdgeType | NodeType):
        if len(move.unsafe_intervals) == 0:
            return float('inf'), 0.0
        
        zlist = list(zip(move.unsafe_intervals, move.unsafe_intervals[1:]))
        for a, b in zlist:
            if a.by_agent == self:
                return b.start - a.end, a.local_recovery_time

        if move.unsafe_intervals[-1].by_agent == self:
            return float('inf'), move.unsafe_intervals[-1].local_recovery_time
        return float('inf'), 0.0

    def calculate_flexibility(self):
        """Calculate the buffer time (bt) and compound recovery time (crt) of the agent.

        Uses the local recovery time stored in an unsafe interval (that is how much can the agent responsible for creating the unsafe interval recover in that interval).
        """
        compound_recovery_time = 0.0

        last_buffer_time = self.max_buffer
        for move in self.route[::-1]:
            local_buffer, local_recovery = self._get_local_flexibility(move)
            logger.info(f"Agent {self.id} with move {move} has local buffer {local_buffer} and recovery {local_recovery}")

            # Because we are going backwards over the route,
            # the buffer time cannot be larger than the buffer time in the future
            # (if ignoring recovery time)
            last_buffer_time = min(last_buffer_time, max(0, local_buffer))

            # Buffer time can increase by recovery time if it would fit
            compound_recovery_time += local_recovery
            last_buffer_time = min(last_buffer_time + local_recovery, self.max_buffer)

            # Store the buffer and crt
            move.add_flexibility(self, last_buffer_time, compound_recovery_time)

    def plot_route(self, ax: Axis, **kwargs):
        x = 0
        location_labels = []
        for move in self.route:
            try:
                length = move.length
                color = "red"
            except AttributeError:
                length = 0
                color = "blue"
                move.append_label(location_labels, x)
            move.plot_unsafe_interval(ax, x, x + length, **kwargs, edgecolor=color)
            x += length
        ticks, labels = list(zip(*location_labels))
        ax.set_xticks(ticks, labels)

        ax.set_xlabel(kwargs.get('xlabel', 'Location'))
        ax.set_ylabel(kwargs.get('ylabel', 'Time'))
        ax.set_title(kwargs.get('title', 'Unsafe Intervals'))

    def get_wait_location(self, initial_location: NodeType, opposing_route: set[EdgeType | NodeType]):
        from flexsipp.graphs.graph import Node
        delayed_at = [initial_location]
        try:
            i = self.route.index(initial_location)
            while i > 0:
                i -= 1
                wait_location = self.route[i]
                delayed_at.append(wait_location)
                if isinstance(wait_location, Node):
                    if wait_location not in opposing_route:
                        return delayed_at
        except ValueError:
            pass
        return delayed_at


    def __repr__(self):
        return f"{self.id}"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)