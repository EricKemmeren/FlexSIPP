from typing import Tuple, Dict

from flexsipp_mapf.graph import Grid
from flexsipp_mapf.agent import MapfAgent
from flexsipp.util.intervals import UnsafeInterval


def paths_to_unsafe_intervals(path_file, grid, scenario_end):
    with open(path_file, "r") as f:
        lines = f.readlines()
        if scenario_end is None:
            grid.global_end_time = max([len(l.split(": ")[1].split("->"))-1 for l in lines])
        else:
            grid.global_end_time = int(scenario_end)
        agents: dict[int, MapfAgent] = {}
        for line in lines:
            name, path = line.strip().split(": ")
            id = int(name.split("Agent ")[1])+1
            node_list = get_coordinate_list(path)
            current_flexibility = 0
            agent = MapfAgent(id, [], grid.global_end_time)
            # Last node is empty
            for i in range(1, len(node_list)):
                if node_list[i] == node_list[i-1]:
                    current_flexibility += 1
                else:
                    # Duration is always one for grids
                    edge_interval = UnsafeInterval(i-1, i, 1, agent, 0)
                    node_interval = UnsafeInterval(i-1-current_flexibility, i, current_flexibility+1, agent, current_flexibility)
                    grid.nodes[node_list[i-1]].add_unsafe_interval(node_interval)
                    agent.wait_time_at_location[grid.nodes[node_list[i-1]]] = current_flexibility

                    edge = None
                    for e in grid.nodes[node_list[i-1]].outgoing:
                        if e.to_node.name == node_list[i]:
                            edge = e

                    assert edge is not None, f"ERROR: cannot find edge from {node_list[i-1]} to {node_list[i]} in grid.\n{grid.nodes[node_list[i-1]].outgoing}"
                    agent.route.append(edge.from_node)
                    agent.route.append(edge)
                    edge.add_unsafe_interval(edge_interval)

                    current_flexibility = 0
                if i == len(node_list) - 1:
                    node_interval = UnsafeInterval(i - current_flexibility, grid.global_end_time, grid.global_end_time - i, agent, grid.global_end_time - i + current_flexibility)
                    grid.nodes[node_list[i]].add_unsafe_interval(node_interval)
                    agent.wait_time_at_location[grid.nodes[node_list[i]]] = grid.global_end_time - i
                    agent.route.append(grid.nodes[node_list[i]])              
            agents[id] = agent
        return agents
    
def get_coordinate_list(node_list):
    nodes = node_list.split("->")
    coordinates = []
    for i, node in enumerate(nodes):
        # Last node is empty
        if i < len(nodes)-1:
            # The list is formatted as coordinates (y,x) separated by ->
            y, x = node.replace(")", "").replace("(", "").split(",")
            coordinates.append(f"({x},{y})")
    return coordinates

def create_mapf_instance_from_paths(location_file, paths_file, scenario_end_time) -> Tuple[Grid, Dict[int, MapfAgent]]:
    grid = Grid.read_graph(location_file)
    agents = paths_to_unsafe_intervals(paths_file, grid, scenario_end_time)

    merge_list = list(grid.nodes.values()) + grid.edges
    for node in merge_list:
        node.merge_unsafe_intervals()
    return grid, agents
