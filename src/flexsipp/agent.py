from typing import Generic

from .util.types import EdgeType, NodeType

class Agent(Generic[EdgeType, NodeType]):

    def __init__(self, id:int, route: list[EdgeType]):
        self.id = id
        self.route: list[EdgeType] = route

    @staticmethod
    def calculate_route(start: NodeType, stops: list[NodeType], **kwargs):
        route: list[EdgeType] = []
        previous_stop = start

        for next_stop in stops:
            route += (previous_stop.calculate_path(next_stop))
            previous_stop = next_stop

        return route

    @property
    def origin(self) -> NodeType:
        return self.route[0].from_node

    @property
    def destination(self) -> NodeType:
        return self.route[-1].to_node

    def _get_local_flexibility(self, move: EdgeType):
        zlist = list(zip(move.unsafe_intervals, move.unsafe_intervals[1:]))
        for a, b in zlist:
            if a.by_agent == self:
                return b.start - a.end, a.local_recovery_time

        if move.unsafe_intervals[-1].by_agent == self:
            return float('inf'), move.unsafe_intervals[-1].local_recovery_time
        return float('inf'), 0.0

    def calculate_flexibility(self):
        compound_recovery_time = 0.0

        max_buffer = float("inf")
        last_buffer_time = max_buffer
        for move in self.route[::-1]:
            local_buffer, local_recovery = self._get_local_flexibility(move)

            # TODO: check order of these operations
            # Because we are going backwards over the route,
            # the buffer time cannot be larger than the buffer time in the future
            # (if ignoring recovery time)
            last_buffer_time = min(last_buffer_time, local_buffer)

            # Buffer time can increase by recovery time if it would fit
            compound_recovery_time += local_recovery
            last_buffer_time = min(last_buffer_time, max_buffer)

            # Store the buffer and crt
            move.add_flexibility(self, last_buffer_time, compound_recovery_time)

    def __repr__(self):
        return f"{self.id}"

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)