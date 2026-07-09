from flexsipp.agent import Agent
from flexsipp.graphs.graph import Node, Edge

class MapfAgent(Agent):
    def __init__(self, id: int, route: list, global_end_time: int):
        super().__init__(id, route)
        self.global_end_time = global_end_time
        self.max_buffer = 10

    def _get_local_flexibility(self, move):
        if len(move.unsafe_intervals) == 0:
            return self.global_end_time, 0.0

        zlist = list(zip(move.unsafe_intervals, move.unsafe_intervals[1:]))
        for a, b in zlist:
            if a.by_agent == self:
                return b.start - a.end, a.local_recovery_time

        last_move = move.unsafe_intervals[-1]
        if last_move.by_agent == self:
            return self.global_end_time - last_move.end, last_move.local_recovery_time
        return self.global_end_time, 0.0
