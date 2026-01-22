import subprocess
from logging import getLogger
from typing import Generic

from .graph import Graph
from ..util.intervals import SafeInterval, FlexibleArrivalTimeFunction
from ..util.results import Results
from ..util.types import EdgeType, NodeType

logger = getLogger('__main__.' + __name__)


class FSIPP(Generic[EdgeType, NodeType]):
    def __init__(self, g:Graph[EdgeType, NodeType], heuristic):
        g.invert_unsafe_intervals()
        self.atfs: list[FlexibleArrivalTimeFunction] = []
        self.g = g

        for node in g.nodes.values():
            def create_atf(from_interval: SafeInterval, edge_interval: SafeInterval, to_interval: SafeInterval, delta):
                h = heuristic[node.name] if node.name in heuristic else 0
                flex_atf = FlexibleArrivalTimeFunction(from_interval, edge_interval, to_interval, delta, h)
                if flex_atf:
                    self.atfs.append(flex_atf)
            [create_atf(*c) for c in node.get_safe_connections()]

    def write(self, file):
        with open(file, 'wt') as f:
            f.write(f"vertex count: {str(len([x for node in self.g.nodes.values() for x in node.safe_intervals]))}\n")
            f.write(f"edge count: {str(len(self.atfs))}\n")

            # Create an index map that maps the safe interval index (in any arbitrary range) to an index starting from 0.
            interval_index_map: dict[int, int] = {}
            last_index = 0

            for node in self.g.nodes.values():
                for interval in node.safe_intervals:
                    f.write(f"{node.name} {repr(interval)}\n")
                    interval_index_map[interval.index] = last_index
                    last_index += 1

            num_trains = 0
            for atf in self.atfs:
                # TODO: recreate atfs such that from_id and to_id start at 0 (or 1?), also for agents
                atf = atf.replace_index(interval_index_map)
                f.write(f"{repr(atf)}\n")
                num_trains = max(num_trains, atf.train_before.id, atf.train_after.id)
            f.write(f"num_trains {num_trains}\n")

    def run_search(self, timeout, origin, destination, start_time, file="flexsipp.txt") -> Results:
        self.write(file)
        try:
            proc = subprocess.run(["flexsipp.exe",
                                   "--start", str(origin),
                                   "--goal", str(destination),
                                   "--edgegraph", str(file),
                                   "--search", "repeat",
                                   "--startTime", str(start_time)
                                   ], timeout=timeout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  encoding='utf-8')
        except subprocess.TimeoutExpired:
            logger.error(f'Timeout for repeat ({timeout}s) expired')
            raise RuntimeError
        if int(proc.returncode) != 0:
            logger.error(f'Search failed for repeat, ec: {proc.returncode}')
            raise RuntimeError
        return Results(str(proc.stdout))
