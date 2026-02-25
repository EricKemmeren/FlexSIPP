from .graphs.graph import Graph, Node, Edge
from .agent import Agent
from .util.intervals import UnsafeInterval

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

class GridConnection(Edge["GridCell", "GridConnection"]):
    def __init__(self, f, t, length, max_speed):
        super().__init__(f, t, length, max_speed)
        self.opposites: list[GridConnection] = []

class Grid(Graph[Node, Edge]):
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
                            if z > 4 and lines[z-1][x] in node_types["passable"]:
                                prev_cell = grid.nodes[f"({x},{y-1})"]
                                e1 = GridConnection(prev_cell, cell, 1, 1)
                                e2 = GridConnection(cell, prev_cell, 1, 1)
                                e1.opposites.append(e2)
                                e2.opposites.append(e1)
                                grid.add_edge(e1)
                                grid.add_edge(e2)
                            if x > 0 and lines[z][x-1] in node_types["passable"]: 
                                prev_cell = grid.nodes[f"({x-1},{y})"]
                                e1 = GridConnection(prev_cell, cell, 1, 1)
                                e2 = GridConnection(cell, prev_cell, 1, 1)
                                e1.opposites.append(e2)
                                e2.opposites.append(e1)
                                grid.add_edge(e1)
                                grid.add_edge(e2)
                return grid
            else:
                print(f"Unknown type of map: {graph_type}")

def paths_to_safe_intervals(path_file, grid, scenario_end):
    with open(path_file, "r") as f:
        lines = f.readlines()
        if scenario_end is None:
            grid.global_end_time = max([len(l.split(": ")[1].split("->"))-1 for l in lines])
        else:
            grid.global_end_time = int(scenario_end)
        agents = []
        for line in lines:
            name, path = line.strip().split(": ")
            id = int(name.split("Agent ")[1])
            node_list = path.split("->")
            current_flexibility = 0
            route = []
            # Last node is empty
            for i in range(1, len(node_list)- 1):
                if node_list[i] == node_list[i-1]:
                    current_flexibility += 1
                else:
                    print(f"Agent {id} at node {node_list[i-1]} at time {i-1} with flex {current_flexibility}")
                    # Duration is always one for grids
                    edge_interval = UnsafeInterval(i-1, i, 1, id, current_flexibility)
                    node_interval = UnsafeInterval(i-1-current_flexibility, i, current_flexibility+1, id, 0)
                    print("Edge:", edge_interval, "node: ", node_interval)
                    grid.nodes[node_list[i-1]].add_unsafe_interval(node_interval)
                    edge = None
                    for e in grid.nodes[node_list[i-1]].outgoing:
                        if e.to_node.name == node_list[i]:
                            edge = e
                    if edge is None:
                        print(f"ERROR: cannot find edge from {node_list[i-1]} to {node_list[i]} in grid.\n{grid.nodes[node_list[i-1]].outgoing}")
                        exit(1)
                    route.append(e)
                    e.add_unsafe_interval(edge_interval)
                    current_flexibility = 0
                if i == len(node_list) - 2:
                    print(f"Agent {id} at node {node_list[i]} at time {i} until end {grid.global_end_time}")
                    node_interval = UnsafeInterval(i-1-current_flexibility, i, current_flexibility+1, id, 0)
                    grid.nodes[node_list[i]].add_unsafe_interval(UnsafeInterval(i, grid.global_end_time, grid.global_end_time - i, id, grid.global_end_time - i))
            for x in route:
                print(x, x.unsafe_intervals)
            agents.append(Agent(id, route))
        return agents

def create_mapf_instance_from_paths(location_file, paths_file, scenario_end_time):
    grid = Grid.read_graph(location_file)
    print(grid)
    agents = paths_to_safe_intervals(paths_file, grid, scenario_end_time)

    merge_list = list(grid.nodes.values()) + grid.edges
    for node in merge_list:
        node.merge_unsafe_intervals()
    for agent in agents:
        agent.calculate_flexibility()
    return grid, agents
