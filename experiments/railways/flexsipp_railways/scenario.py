from pathlib import Path
from typing import Union, Tuple, Any
from logging import getLogger

import time
import numpy as np
from matplotlib import cm
from matplotlib.axis import Axis

from flexsipp.graphs.graph import IntervalStore
from flexsipp.util.timing import timing

from .track_graph import TrackEdge
from .block_graph import BlockGraph, BlockNode, BlockEdge
from .train_agent import TrainItem, TrainAgent

logger = getLogger('__main__.' + __name__)


class Scenario:
    @timing(Path(__file__).parent)
    def __init__(self, data, g_block: BlockGraph, agent_cls):
        self.types = {x["name"]: x for x in data["types"]}
        self.g = g_block

        if self.g.global_end_time is None:
            self.g.global_end_time = max([2 * entry["movements"]["endTime"] for entry in data["trains"]])
            self.g.tg.global_end_time = self.g.global_end_time
        self.agents: dict[str, TrainAgent] = {}

        # Calculate routes for all trains
        for id, train in enumerate(data["trains"], start=1):
            train_type = self.types[train["trainUnitTypes"][0]]
            movements = train["movements"]
            measures = TrainItem(
                sum([self.types[x]["length"] for x in train["trainUnitTypes"]]),
                train_type["speed"] / 3.6,
                train_type["acceleration"],
                train_type["deceleration"],
                data["walkingSpeed"],
                train_type["minimum_station_time"],
                data["sightReactionTime"],
                data["setupTime"],
                data["releaseTime"],
                movements["startTime"]
            )
            # TODO: check if its from from_node or from to_node
            start = g_block.get_block_from_station(movements["startLocation"])
            stops: list[BlockNode] = []

            for stop in movements["stops"]:
                loc = stop["location"]
                next = g_block.get_block_from_station(loc)
                direction = g_block.get_initial_direction(start, next, measures.train_speed)
                stops.append(start[direction])
                start = next

            end = g_block.get_block_from_station(movements["endLocation"])
            direction = g_block.get_initial_direction(start, end, measures.train_speed)
            stops.append(start[direction])

            end_a, end_b = end
            dist_a = g_block.distance_between_nodes(start[direction], end_a, measures.train_speed)
            dist_b = g_block.distance_between_nodes(start[direction], end_b, measures.train_speed)
            if dist_a <= dist_b:
                direction = 0
            else:
                direction = 1
            stops.append(end[direction])
            agent = agent_cls(id, agent_cls.calculate_route(stops[0], stops[1:]), measures)
            self.agents[train['trainNumber']] = agent

    @timing(Path(__file__).parent)
    def process_blocking_time_intervals(self):
        for i, agent in enumerate(self.agents.values()):
            start_time = time.time()
            agent.calculate_blocking_times()
            logger.info(f"{i}/{len(self.agents)}: Agent {agent} calculated blocking times in {time.time() - start_time} for {len(agent.route)} blocks in route")
            merge_list: list[IntervalStore] = list(self.g.nodes.values()) + self.g.edges
            for node in merge_list:
                IntervalStore.merge_unsafe_intervals(node)

    @timing(Path(__file__).parent)
    def compute_flexibility(self):
        for agent in self.agents.values():
            agent.calculate_flexibility()
        logger.info("Calculated flexibility for all agents")

    def get_replanning_agent(self, a: Union[TrainAgent, int, str]) -> TrainAgent:
        if isinstance(a, str):
            return self.agents[a]
        if isinstance(a, int):
            return list(self.agents.values())[a - 1]
        return a

    @timing(Path(__file__).parent)
    def fsipp(self, agent: Union[TrainAgent, int, str]) -> BlockGraph:
        """
        Create a BlockGraph that can be used by FSIPP.
        First filter out the unsafe intervals for the agent that we want to run flexSIPP on.
        Then convert the edge length to be time instead of distance.
        @param agent: Agent_id to filter out, or a new agent in the simulation.
        @return: Copy of the BlockGraph that is updated to filter out agent
        """
        g = self.g
        agent = self.get_replanning_agent(agent)
        assert agent is not None
        uis:list[IntervalStore] = list(g.nodes.values()) + g.edges
        for ui in uis:
            ui.filter_out_agent(agent)
        for e in g.edges:
            e.length = e.length / agent.measures.train_speed

        return g

    def plot_blocking_staircase(self, ax: Axis, agent: Union[TrainAgent, int, str], **kwargs):
        agent = self.get_replanning_agent(agent)
        track_edges_to_plot: dict[TrackEdge, Tuple[float, float]] = {}
        block_edges_to_plot: dict[BlockEdge, Tuple[float, float]] = {}
        x = 0
        x_b = 0
        x_ticks: Tuple[list[float], list[str]] = ([], [])
        for block in agent.route:
            x_ticks[0].append(x)
            x_ticks[1].append(block.from_node.name)
            for e in block.track_route:
                track_edges_to_plot[e] = (x, x + e.length)
                for opp_e in e.opposites:
                    track_edges_to_plot[opp_e] = (x + e.length, x)
                x += e.length
            block_edges_to_plot[block] = (x_b, x)
            # assert x - x_b == block.length
            x_b = x

        x_ticks[0].append(x)
        x_ticks[1].append(agent.route[-1].to_node.name)
        ax.set_xticks(x_ticks[0], labels=x_ticks[1])
        ax.grid()

        color = iter(cm.rainbow(np.linspace(0, 1, len(self.agents))))
        agent_to_color:dict[int, Any] = {}
        for a in self.agents:
            c = next(color)
            a.plot_route(ax, track_edges_to_plot, c)
            agent_to_color[a.id] = c

        for block, (x1, x2) in block_edges_to_plot.items():
            block.plot_unsafe_interval(ax, x1, x2, agent_to_color)
            