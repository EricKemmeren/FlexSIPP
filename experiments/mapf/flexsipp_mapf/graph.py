from .agent import MapfAgent
from flexsipp.graphs.graph import Node, Edge, Graph
from flexsipp.util.intervals import UnsafeInterval

### Node types in MovingAI benchmark maps ###
node_types = {
    "passable": [".", "G"],
    "out-of-bounds": ["@", "O"],
    "other": ["T", "S", "W"]
# . - passable terrain
# G - passable terrain
# @ - out of bounds
# O - out of bounds
# T - trees (unpassable)
# S - swamp (passable from regular terrain)
# W - water (traversable, but not passable from terrain)
}

class GridCell(Node["GridConnection", "GridCell"]):
    def __init__(self, name):
        super().__init__(name)
        self.old_unsafe_intervals = None

    def filter_out_agent(self, agent: MapfAgent):
        # Before filtering out the agents, store the unsafe intervals
        self.old_unsafe_intervals = self.unsafe_intervals
        super().filter_out_agent(agent)

class GridConnection(Edge["GridConnection", "GridCell"]):
    def __init__(self, f, t, length, max_speed):
        super().__init__(f, t, length, max_speed)
        self.opposite: GridConnection = None
        self.old_unsafe_intervals = None

    def add_unsafe_interval(self, interval: UnsafeInterval, original = True):
        super().add_unsafe_interval(interval)
        super(Edge, self.opposite).add_unsafe_interval(interval)
        # if original:
        #     self.to_node.add_unsafe_interval(interval)

    def remove_unsafe_interval(self, interval: UnsafeInterval):
        super().remove_unsafe_interval(interval)
        super(Edge, self.opposite).remove_unsafe_interval(interval)
        # self.to_node.remove_unsafe_interval(interval)

    def add_flexibility(self, agent: MapfAgent, bt: float, crt:float):
        """
        Add the flexibility parameters to this node/edge
        @param agent: Agent for which the bt and crt are defined
        @param bt: Buffer Time at this node/edge
        @param crt: Compound Recovery Time at this node/edge
        """
        super().add_flexibility(agent, bt, crt)
        super(Edge, self.opposite).add_flexibility(agent, bt, crt)

    def filter_out_agent(self, agent: MapfAgent):
        # Before filtering out the agents, store the unsafe intervals
        self.old_unsafe_intervals = self.unsafe_intervals
        super().filter_out_agent(agent)

class Grid(Graph[Edge, Node]):
    def __init__(self, w, h):
        super().__init__()
        self.width = w
        self.height = h

    def __repr__(self) -> str:
        return f"Grid {self.width}x{self.height} with {len(self.edges)} edges and {len(self.nodes)} nodes"

    def display_graph(self):
        for node in self.nodes:
            print(f"Node {node} with outgoing {self.nodes[node].outgoing}")

    @classmethod
    def read_graph(cls, file_name):
        with open(file_name, "r") as f:
            lines = f.readlines()
            graph_type = lines[0].strip().split("type ")[1]
            if graph_type == "octile":
                height = int(lines[1].strip().split("height ")[1])
                width = int(lines[2].strip().split("width ")[1])
                grid = cls(width, height)
                for y in range(height):
                    z = y + 4
                    for x in range(width):
                        if lines[z][x] in node_types["passable"]:
                            grid.add_node(GridCell(f"({x},{y})"))
                            cell = grid.nodes[f"({x},{y})"]
                            if z > 4 and lines[z - 1][x] in node_types["passable"]:
                                prev_cell = grid.nodes[f"({x},{y - 1})"]
                                e1 = GridConnection(prev_cell, cell, 1, 1)
                                e2 = GridConnection(cell, prev_cell, 1, 1)
                                e1.opposite = e2
                                e2.opposite = e1
                                grid.add_edge(e1)
                                grid.add_edge(e2)
                            if x > 0 and lines[z][x - 1] in node_types["passable"]:
                                prev_cell = grid.nodes[f"({x - 1},{y})"]
                                e1 = GridConnection(prev_cell, cell, 1, 1)
                                e2 = GridConnection(cell, prev_cell, 1, 1)
                                e1.opposite = e2
                                e2.opposite = e1
                                grid.add_edge(e1)
                                grid.add_edge(e2)
                return grid
            else:
                print(f"Unknown type of map: {graph_type}")

    def _complete_new_route(self, new_route: list):
        route_with_edges = []
        node_route = [node for node in new_route if isinstance(node[0], Node)]
        zlist = list(zip(node_route, node_route[1:]))
        for from_node, to_node in zlist:
            for edge in from_node[0].outgoing:
                if edge.to_node == to_node[0]:
                    route_with_edges += [from_node, (edge, [0, self.global_end_time])]
        return route_with_edges + [node_route[-1]]

    def _update_delayed_agent(self, agent: MapfAgent, new_route: list, actual_departure_time: float):
        route_with_edges, safe_intervals = list(zip(*self._complete_new_route(new_route))) #TODO, actually calculate the route with edges in c code

        # Copy over all unsafe intervals from the part of the route before the agent is delayed
        existing_route = agent.route[:agent.route.index(route_with_edges[0])]
        for move in existing_route:
            for ui in move.old_unsafe_intervals:
                if ui.by_agent == agent:
                    move.add_unsafe_interval(ui)

        current_time = actual_departure_time
        # Calculate new route for the agent, it departs from new_route[0] with a delay of actual_delay, always departing as soon as the next node is safe.
        for i, move in enumerate(route_with_edges[:-1]):
            if isinstance(move, GridConnection):
                from_node = move.from_node
                to_node = move.to_node

                si_from = safe_intervals[i-1]
                si_edge = safe_intervals[i]
                si_to   = safe_intervals[i+1]

                earliest_departure = max(si_edge[0], si_to[0] - move.length, current_time)

                recovery_time = earliest_departure - current_time

                from_node.add_unsafe_interval(UnsafeInterval(current_time, earliest_departure + 1, recovery_time, agent, recovery_time))
                agent.wait_time_at_location[from_node] = recovery_time
                move.add_unsafe_interval(UnsafeInterval(earliest_departure, earliest_departure + move.length, move.length, agent, 0))

                current_time = earliest_departure + move.length

        # Node where the agent is delayed in, is unsafe from the moment it arrives there
        for ui in route_with_edges[0].unsafe_intervals:
            if ui.by_agent == agent:
                for old_ui in route_with_edges[0].old_unsafe_intervals:
                    if old_ui.by_agent == agent:
                        ui.start = old_ui.start
                        ui.local_recovery_time = ui.end - 1 - ui.start
                        agent.wait_time_at_location[route_with_edges[0]] = ui.local_recovery_time

        # At the end of it's route the node stays unsafe
        last_ui = UnsafeInterval(current_time, self.global_end_time, self.global_end_time - current_time, agent, self.global_end_time - current_time)
        agent.wait_time_at_location[route_with_edges[-1]] = self.global_end_time - current_time
        route_with_edges[-1].add_unsafe_interval(last_ui)

        agent.route = existing_route + list(route_with_edges)
