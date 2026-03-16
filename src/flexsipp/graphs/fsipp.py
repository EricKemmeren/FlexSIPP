import os
import io
import time
from logging import getLogger
from typing import Generic, TextIO, Iterable, Any

from .. import search
from .graph import Graph
from ..agent import Agent
from ..util.intervals import SafeInterval, FlexibleArrivalTimeFunction
from ..util.results import Results
from ..util.timing import timing
from ..util.types import EdgeType, NodeType

logger = getLogger('__main__.' + __name__)

import os
from contextlib import contextmanager

@contextmanager
def redirect_cpp_output(stdout_path, stderr_path):
    stdout_fd = os.open(stdout_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    stderr_fd = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    old_stdout = os.dup(1)
    old_stderr = os.dup(2)

    os.dup2(stdout_fd, 1)
    os.dup2(stderr_fd, 2)

    try:
        yield
    finally:
        os.dup2(old_stdout, 1)
        os.dup2(old_stderr, 2)
        os.close(stdout_fd)
        os.close(stderr_fd)
        os.close(old_stdout)
        os.close(old_stderr)

class FSIPP(Generic[EdgeType, NodeType]):
    def __init__(self, g:Graph[EdgeType, NodeType], heuristic:dict[str, float], agents: dict[Any, Agent], filter_nodes:Iterable[NodeType]=None, use_flexibility=True):
        """ Create a flexible safe interval any-start-time graph of the given graph, that can be used to run the search algorithm.

        :param Graph g: Graph containing the nodes and edges with populated unsafe intervals. Edge length should be duration.
        :param dict heuristic: Dictionary that maps node name to a value, this value is used as the heuristic in the A* search.
        :param Iterable agents: Number of agents present is the graph.
        :param Iterable, optional filter_nodes: Optional argument to specify the allowed nodes the new agent is able to find a new path over.
        :param Bool use_flexibility: when set to False, the agents do not have any flexibility and regular @MAEDeR search is performed.
        :return: A FlexSIPP graph with SafeIntervals on the nodes, and FlexibleArrivalTimeFunctions between these nodes as edges.
        """
        g.reset_flexibility()
        if use_flexibility:
            for agent in agents.values():
                agent.calculate_flexibility()
        g.invert_unsafe_intervals()
        self.atfs: list[FlexibleArrivalTimeFunction] = []
        self.num_agents = len(agents)
        self.g = g

        if filter_nodes:
            self.nodes = filter_nodes
        else:
            self.nodes = set(g.nodes.values())
        # TODO: maybe force self.nodes to be a set(), does remove ordering making manual reading of file more difficult

        for node in self.nodes:
            def create_atf(from_interval: SafeInterval, edge_interval: SafeInterval, to_interval: SafeInterval, edge):
                h = heuristic[edge.to_node.name] if edge.to_node.name in heuristic else 0
                flex_atf = FlexibleArrivalTimeFunction(from_interval, edge_interval, to_interval, edge.length, h)
                if flex_atf:
                    logger.debug(f"Node {node.name} has flex ATF zeta {flex_atf.zeta} alpha {flex_atf.alpha}, beta {flex_atf.beta}, delta {flex_atf.delta}  Before agent {flex_atf.train_before} crt {flex_atf.crt_before} and after agent {flex_atf.train_after} buffer {flex_atf.buffer_after} and crt {flex_atf.crt_after}")
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

    def run_search(self, origin, destination, start_time, max_delay=1000, **kwargs) -> Results:
        """ Search on the FSIPP graph.

        :param origin: Start location of the search.
        :param destination: Location to search to.
        :param start_time: Time to start searching from. At start_time, the origin should be safe to visit.
        :param max_delay: Search for paths starting between start_time and start_time+max_delay (default=1000).
        :param optimize_total_delay: If True, return the first path that optimizes the total delay for all agents in the simulation.
        :param redirect_stdout: file to redirect the output stream from the c++ search to.
        :param redirect_stderr: file to redirect the error output stream from the c++ search to.
        """
        graph = io.StringIO()
        self._write(graph)
        graph = graph.getvalue()
        log_time_start = time.time()
        with redirect_cpp_output(kwargs.get("redirect_stdout", os.devnull), kwargs.get("redirect_stderr", os.devnull)):
            result = search.search(str(origin), str(destination), graph, start_time, max_delay, kwargs.get("optimize_total_delay", False))
        log_time_end = time.time()
        return Results.parse_json(result, self.g, log_time_end - log_time_start)
