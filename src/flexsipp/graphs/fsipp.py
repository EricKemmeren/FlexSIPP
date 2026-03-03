import os
import io
from logging import getLogger
from typing import Generic, TextIO, Iterable
from contextlib import redirect_stderr

from .. import search
from .graph import Graph
from ..util.intervals import SafeInterval, FlexibleArrivalTimeFunction
from ..util.results import Results
from ..util.types import EdgeType, NodeType

logger = getLogger('__main__.' + __name__)

class FSIPP(Generic[EdgeType, NodeType]):
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
        self.g = g

        if filter_nodes:
            self.nodes = filter_nodes
        else:
            self.nodes = g.nodes.values()
        # TODO: maybe force self.nodes to be a set(), does remove ordering making manual reading of file more difficult

        for node in self.nodes:
            def create_atf(from_interval: SafeInterval, edge_interval: SafeInterval, to_interval: SafeInterval, edge):
                h = heuristic[edge.to_node.name] if edge.to_node.name in heuristic else 0
                flex_atf = FlexibleArrivalTimeFunction(from_interval, edge_interval, to_interval, edge.length, h)
                if flex_atf:
                    self.atfs.append(flex_atf)
            [create_atf(*c) for c in node.get_safe_connections(self.nodes)]

    def _write(self, f:TextIO):
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

    # def run_search(self, timeout, origin, destination, start_time, file="flexsipp.txt") -> Results:
    #     with open(file, 'wt') as f:
    #         self.write(f)
    #     try:
    #         proc = subprocess.run(["flexsipp.exe",
    #                                "--start", str(origin),
    #                                "--goal", str(destination),
    #                                "--edgegraph", str(file),
    #                                "--search", "repeat",
    #                                "--startTime", str(start_time)
    #                                ], timeout=timeout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    #                               encoding='utf-8')
    #     except subprocess.TimeoutExpired:
    #         logger.error(f'Timeout for repeat ({timeout}s) expired')
    #         raise RuntimeError
    #     if int(proc.returncode) != 0:
    #         logger.error(f'Search failed for repeat, ec: {proc.returncode}')
    #         raise RuntimeError
    #     return Results(str(proc.stdout))

    def run_search(self, timeout, origin, destination, start_time) -> Results:
        """ Search on the FSIPP graph.

        :param timeout: Max search duration in seconds.
        :param origin: Start location of the search.
        :param destination: Location to search to.
        :param start_time: Time to start searching from. At start_time, the origin should be safe to visit.
        """
        graph = io.StringIO()
        self._write(graph)
        graph = graph.getvalue()
        # with open(os.path.join(os.path.dirname(__file__), "search_stderr.txt"), "w") as f:
            # with redirect_stderr(f):
        result = search.search(str(origin), str(destination), graph, start_time, timeout)
        return Results.parse_json(result, self.g)
