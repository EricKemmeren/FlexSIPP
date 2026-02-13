import subprocess
from logging import getLogger
from typing import Generic, Iterable

from .graph import Graph
from ..util.intervals import SafeInterval, FlexibleArrivalTimeFunction
from ..util.results import Results
from ..util.types import EdgeType, NodeType
from ..util.timing import timing

logger = getLogger('__main__.' + __name__)


class FSIPP(Generic[EdgeType, NodeType]):
    @timing
    def __init__(self, g:Graph[EdgeType, NodeType], heuristic:dict[str, float], num_agents: int, filter_nodes:Iterable[NodeType]=None):
        """ Create a flexibile safe interval any-start-time graph of the given graph, that can be used to run the search algorithm.

        :param Graph g: Graph containing the nodes and edges with populated unsafe intervals. Edge length should be duration.
        :param dict heuristic: Dictionary that maps node name to a value, this value is used as the heuristic in the A* search.
        :param int num_agents: Number of agents present is the graph.
        :param Iterable, optional filter_nodes: Optional argument to specify the allowed nodes the new agent is able to find a new path over.
        :return: A FlexSIPP graph with SafeIntervals on the nodes, and FlexibleArrivalTimeFunctions between these nodes as edges.
        """
        g.invert_unsafe_intervals()
        self.atfs: list[FlexibleArrivalTimeFunction] = []
        self.num_agents = num_agents

        if filter_nodes:
            self.nodes = filter_nodes
        else:
            self.nodes = g.nodes.values()

        for node in self.nodes:
            def create_atf(from_interval: SafeInterval, edge_interval: SafeInterval, to_interval: SafeInterval, delta):
                h = heuristic[node.name] if node.name in heuristic else 0
                flex_atf = FlexibleArrivalTimeFunction(from_interval, edge_interval, to_interval, delta, h)
                if flex_atf:
                    self.atfs.append(flex_atf)
            [create_atf(*c) for c in node.get_safe_connections(self.nodes)]

    def _write(self, file):
        with open(file, 'wt') as f:
            f.write(f"vertex count: {str(len([x for node in self.nodes for x in node.safe_intervals]))}\n")
            f.write(f"edge count: {str(len(self.atfs))}\n")

            # Create an index map that maps the safe interval index (in any arbitrary range) to an index starting from 0.
            interval_index_map: dict[int, int] = {}
            last_index = 0

            for node in self.nodes:
                for interval in node.safe_intervals:
                    f.write(f"{node.name} {repr(interval)}\n")
                    interval_index_map[interval.index] = last_index
                    last_index += 1

            for atf in self.atfs:
                atf = atf.replace_index(interval_index_map)
                f.write(f"{repr(atf)}\n")
            f.write(f"num_trains {self.num_agents}\n")

    @timing
    def run_search(self, timeout, origin, destination, start_time, file="flexsipp.txt", err_file="stderr.txt") -> Results:
        """ Search on the FSIPP graph.\n
        The executable build from the search/build directory is assumed to be added to the PATH variable, such that it can be executed by running 'flexsipp.exe'.

        :param timeout: Max search duration in seconds.
        :param origin: Start location of the search.
        :param destination: Location to search to.
        :param start_time: Time to start searching from. At start_time, the origin should be safe to visit.
        :param optional file: Location to store the search graph in.
        :param optional err_file: Location to store the stderr output of flexsipp.exe.
        """
        self._write(file)
        print("Running FSIPP: ")
        print(" ".join(["flexsipp.exe",
                                   "--start", str(origin),
                                   "--goal", str(destination),
                                   "--edgegraph", str(file),
                                   "--search", "repeat",
                                   "--startTime", str(start_time)
                                   ]))
        try:
            proc = subprocess.run(["flexsipp.exe",
                                   "--start", str(origin),
                                   "--goal", str(destination),
                                   "--edgegraph", str(file),
                                   "--search", "repeat",
                                   "--startTime", str(start_time)
                                   ], timeout=timeout, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  encoding='utf-8')
        except subprocess.TimeoutExpired as to:
            with open(err_file, "w") as f:
                f.write(to.stderr)
            logger.error(f'Timeout for repeat ({timeout}s) expired')
            raise RuntimeError
        with open(err_file, "w") as f:
            f.write(proc.stderr)
        if int(proc.returncode) != 0:
            logger.error(f'Search failed for repeat, ec: {proc.returncode}')
            raise RuntimeError
        return Results.parse_list_of_outputs(str(proc.stdout))
