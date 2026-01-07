from generation.graphs.graph import Edge, Node


class Agent:
    id = 0

    def __init__(self, route: list[Edge]):
        self.id = Agent.id
        Agent.id += 1

        self.route: list[Edge] = route
        self.buffer_time: dict[Edge, float] = {}
        self.compound_recovery_time: dict[Edge, float] = {}

    @classmethod
    def calculate_route(cls, start: Node, stops: list[Node]):
        route: list[Edge] = []



        return cls(route)

