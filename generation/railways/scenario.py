from copy import copy
from typing import Union, Tuple, Any

import numpy as np
from matplotlib import cm, patches
from matplotlib.axis import Axis

from generation.graphs.graph import IntervalStore
from generation.railways.block_graph import BlockGraph, BlockNode
from generation.railways.track_graph import TrackEdge
from generation.railways.train_agent import TrainItem, TrainAgent
from generation.util.timing import timing
from old_generation.graph import BlockEdge


class Scenario:
    @timing
    def __init__(self, data, g_block: BlockGraph, agent_cls):
        self.types = {x["name"]: x for x in data["types"]}
        self.g = g_block

        self.g.global_end_time = max([2 * entry["movements"]["endTime"] for entry in data["trains"]])
        self.g.tg.global_end_time = self.g.global_end_time
        self.agents: list[TrainAgent] = []

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

            for stop, time in movements["stops"].items():
                next = g_block.get_block_from_station(stop)
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
            self.agents.append(agent)

    @timing
    def process(self):
        for agent in self.agents:
            agent.calculate_blocking_times()
        merge_list: list[IntervalStore] = list(self.g.nodes.values()) + self.g.edges
        for node in merge_list:
            node.merge_unsafe_intervals()
        for agent in self.agents:
            agent.calculate_flexibility()

    def get_replanning_agent(self, a: Union[TrainAgent, int]) -> TrainAgent:
        if isinstance(a, int):
            return self.agents[a - 1]
        return a

    @timing
    def fsipp(self, agent: Union[TrainAgent, int]) -> BlockGraph:
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
            ui.unsafe_intervals = ui.filter_out_agent(agent)
        for e in g.edges:
            e.length = e.length / agent.measures.train_speed

        return g

    def plot_blocking_staircase(self, ax: Axis, agent: Union[TrainAgent, int], **kwargs):
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
            for ui in block.unsafe_intervals:
                c = agent_to_color.get(ui.by_agent.id, None)
                blocking_time = patches.Rectangle((x1, ui.start), x2 - x1, ui.end - ui.start,
                                                  linewidth=1, edgecolor="red", facecolor="none")
                ax.add_patch(blocking_time)
                bt, _ = block.get_flexibility(ui.by_agent)
                buffer_time = patches.Rectangle((x1, ui.end), x2 - x1, bt,
                                                  linewidth=1, edgecolor=c, facecolor=c, alpha=0.5)
                ax.add_patch(buffer_time)
