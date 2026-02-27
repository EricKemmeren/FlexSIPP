from typing import Tuple, Dict

from graph import Grid
from agent import MapfAgent
from flexsipp.util.intervals import UnsafeInterval

def paths_to_safe_intervals(path_file, grid, scenario_end, delay_agent):
    with open(path_file, "r") as f:
        lines = f.readlines()
        if scenario_end is None:
            grid.global_end_time = max([len(l.split(": ")[1].split("->"))-1 for l in lines])
        else:
            grid.global_end_time = int(scenario_end)
        agents: dict[int, MapfAgent] = {}
        for line in lines:
            name, path = line.strip().split(": ")
            id = int(name.split("Agent ")[1])
            node_list = path.split("->")
            current_flexibility = 0
            agent = MapfAgent(id, [], grid.global_end_time)
            # Last node is empty
            for i in range(1, len(node_list)- 1):
                if node_list[i] == node_list[i-1]:
                    current_flexibility += 1
                else:
                    print(f"Agent {agent} at node {node_list[i-1]} at time {i-1} with flex {current_flexibility}")
                    # Duration is always one for grids
                    edge_interval = UnsafeInterval(i-1, i, 1, agent, current_flexibility)
                    node_interval = UnsafeInterval(i-1-current_flexibility, i, current_flexibility+1, agent, 0)
                    print("Edge:", edge_interval, "node: ", node_interval)
                    if delay_agent != id:
                        grid.nodes[node_list[i-1]].add_unsafe_interval(node_interval)
                    edge = None
                    for e in grid.nodes[node_list[i-1]].outgoing:
                        if e.to_node.name == node_list[i]:
                            edge = e

                    assert edge is not None, f"ERROR: cannot find edge from {node_list[i-1]} to {node_list[i]} in grid.\n{grid.nodes[node_list[i-1]].outgoing}"
                    agent.route.append(e)
                    if delay_agent != id:
                        e.add_unsafe_interval(edge_interval)
                    current_flexibility = 0
                if i == len(node_list) - 2:
                    print(f"Agent {id} at node {node_list[i]} at time {i} until end {grid.global_end_time}")
                    node_interval = UnsafeInterval(i-1-current_flexibility, i, current_flexibility+1, agent, 0)
                    if delay_agent != id:
                        grid.nodes[node_list[i]].add_unsafe_interval(UnsafeInterval(i, grid.global_end_time, grid.global_end_time - i, agent, grid.global_end_time - i))
            for x in agent.route:
                print(x, x.unsafe_intervals)
            agents[id] = agent
        return agents

def create_mapf_instance_from_paths(location_file, paths_file, scenario_end_time, delay_agent) -> Tuple[Grid, Dict[int, MapfAgent]]:
    grid = Grid.read_graph(location_file)
    print(grid)
    agents = paths_to_safe_intervals(paths_file, grid, scenario_end_time, delay_agent)

    merge_list = list(grid.nodes.values()) + grid.edges
    for node in merge_list:
        node.merge_unsafe_intervals()
    for agent in agents.values():
        agent.calculate_flexibility()
    return grid, agents
