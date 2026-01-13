from generation.graphs.graph import IntervalStore
from generation.railways.block_graph import BlockGraph, BlockNode
from generation.railways.train_agent import TrainItem, TrainAgent


class Scenario:
    def __init__(self, data, g_block: BlockGraph):
        # self.trains = data["trains"]
        self.types = {x["name"]: x for x in data["types"]}
        self.g = g_block

        self.g.global_end_time = max([2 * entry["movements"]["endTime"] for entry in data["trains"]])
        self.g.tg.global_end_time = self.g.global_end_time
        self.agents: list[TrainAgent] = list()

        # Calculate routes for all trains
        for train in data["trains"]:
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
            start = g_block.get_block_from_station(movements["startLocation"])
            # TODO: check if its from from_node or from to_node
            stops: list[BlockNode] = list()

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

            agent = TrainAgent(TrainAgent.calculate_route(stops[0], stops[1:]), measures)
            self.agents.append(agent)

    def process(self):
        for agent in self.agents:
            agent.calculate_blocking_times()
        merge_list: list[IntervalStore] = list(self.g.nodes.values()) + self.g.edges
        for node in merge_list:
            node.merge_unsafe_intervals()