from logging import getLogger

from generation.graphs.graph import Graph
from generation.util.intervals import SafeInterval

logger = getLogger('__main__.' + __name__)

class ArrivalTimeFunction:
    def __init__(self, from_interval: SafeInterval, edge_interval: SafeInterval, to_interval: SafeInterval, delta):
        self.from_id = from_interval.index
        self.to_id   = to_interval.index
        self.train_before = edge_interval.train_before
        self.train_after  = edge_interval.train_after

        self.zeta = from_interval.start
        self.alpha = max(from_interval.start, edge_interval.start, to_interval.start - delta)
        self.beta = min(from_interval.end, edge_interval.end, to_interval.end - delta)
        self.delta = delta


class FlexibleArrivalTimeFunction(ArrivalTimeFunction):
    def __init__(self, from_interval: SafeInterval, edge_interval: SafeInterval, to_interval: SafeInterval, delta):
        super().__init__(from_interval, to_interval, edge_interval, delta)

        # TODO: fix
        self.buffer_after = 0
        self.crt_after = 0
        # if self.train_after != 0 and o.get_identifier() in buffer_times[train_after]:
        #     buffer_after = buffer_times[train_after][o.get_identifier()]
        #     crt_a = recovery_times[train_after][o.get_identifier()]
        # elif train_after != 0 and print_intervals:
        #     logger.error(f"ERROR - Buffer time not found while it should have one for train {train_after} "
        #                  f"at {o.get_identifier()}")

        self.crt_before = 0
        # if train_before != 0 and o.get_identifier() in recovery_times[train_before]:
        #     crt_b = recovery_times[train_before][o.get_identifier()]
        # elif train_before != 0 and print_intervals:
        #     logger.error(f"ERROR - Recovery time not found while it should have one for train {train_before} "
        #                  f"at {o.get_identifier()}")
        self.heuristic = 0

    def __repr__(self):
        return f"{self.from_id} {self.to_id} {self.zeta} {self.alpha} {self.beta} {self.delta} {self.train_before} {self.crt_before} {self.train_after} {self.buffer_after} {self.crt_after} {self.heuristic}"


class FSIPP:
    def __init__(self, g:Graph, buffer_times):
        g.invert_unsafe_intervals(buffer_times)
        self.atfs: list[ArrivalTimeFunction] = []
        self.g = g

        def create_atf(from_interval: SafeInterval, to_interval: SafeInterval, edge_interval: SafeInterval, delta):
            flex_atf = FlexibleArrivalTimeFunction(from_interval, to_interval, edge_interval, delta)
            self.atfs.append(flex_atf)

        for node in g.nodes.values():
            node.apply_to_safe_connections(create_atf)

    def write(self, file):
        with open(file, 'wt') as f:
            f.write(f"vertex count: {str(len([x for node in self.g.nodes.values() for x in node.safe_intervals]))}")
            f.write(f"edge count: {str(len(self.atfs))}\n")

            for node in self.g.nodes.values():
                for interval in node.safe_intervals:
                    f.write(f"{repr(interval)}\n")

            num_trains = 0
            for atf in self.atfs:
                f.write(f"{repr(atf)}\n")
                num_trains = max(num_trains, atf.train_before, atf.train_after)
            f.write(f"num_trains {num_trains}\n")