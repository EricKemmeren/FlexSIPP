from graph import Grid
from flexsipp.agent import Agent
from flexsipp.util.intervals import UnsafeInterval

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
