from flexsipp.agent import Agent
from flexsipp.graphs.graph import Node, Edge

class MapfAgent(Agent):
    def __init__(self, id: int, route: list, global_end_time: int):
        super().__init__(id, route)
        self.global_end_time = global_end_time
        self.max_buffer = 10
        self.wait_time_at_location = {}

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

    def get_location_at_time(self, time_point):
        current_time = 0
        for loc in self.route:
            if isinstance(loc, Node):
                current_time += self.wait_time_at_location[loc]
                if current_time >= time_point:
                    return loc
            if isinstance(loc, Edge):
                current_time += loc.length
        return self.destination


    def update_wait_time_with_flexibility(self, flexibility_used):
        if flexibility_used:
            current_delay = 0
            for move in self.route:
                filtered_uis = [ui for ui in move.unsafe_intervals if ui.by_agent == self]
                if len(filtered_uis)>0:
                    ui = filtered_uis[0]
                    new_delay = flexibility_used.get(move, 0)
                    if current_delay < new_delay:
                        # Delay becomes larger, thus the agent should wait here. Extend end of interval delay, start of interval is shifted by old delay
                        # As it's standing still here, it is gaining local recovery time by the difference in delay amount
                        if isinstance(move, Node):
                            self.wait_time_at_location[move] = ui.local_recovery_time + new_delay - current_delay
                        current_delay = new_delay
                    else:
                        recovery_used = min(ui.local_recovery_time, current_delay)
                        updated_delay = current_delay - recovery_used
                        if isinstance(move, Node):
                            self.wait_time_at_location[move] = ui.local_recovery_time - recovery_used
                        current_delay = updated_delay
