from flexsipp.agent import Agent
from flexsipp.graphs.graph import Node, Edge, Graph

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

class GridConnection(Edge["GridConnection", "GridCell"]):
    def __init__(self, f, t, length, max_speed):
        super().__init__(f, t, length, max_speed)
        self.opposite: GridConnection = None

    def add_flexibility(self, agent: Agent, bt: float, crt:float):
        """
        Add the flexibility parameters to this node/edge
        @param agent: Agent for which the bt and crt are defined
        @param bt: Buffer Time at this node/edge
        @param crt: Compound Recovery Time at this node/edge
        """
        super().add_flexibility(agent, bt, crt)
        super(Edge, self.opposite).add_flexibility(agent, bt, crt)

class Grid(Graph[Edge, Node]):
    def __init__(self, w, h):
        super().__init__()
        self.width = w
        self.height = h

    def __repr__(self) -> str:
        return f"Grid {self.width}x{self.height} with {len(self.edges)} edges and {len(self.nodes)} nodes"

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
