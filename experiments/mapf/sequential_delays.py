import csv
import argparse
from copy import deepcopy

from matplotlib import pyplot as plt

from flexsipp.graphs.graph import Node
from flexsipp.graphs.fsipp import FSIPP
from read_experiment import create_mapf_instance_from_paths

parser = argparse.ArgumentParser(
                    prog='FlexSIPP',
                    description='Given a location (file) and a scenario (file), run the FlexSIPP program')
parser.add_argument('-l', "--location-file", help = "Path to the location file", required = True)
parser.add_argument('-s', "--scenario-file", help = "Path to the scenario file", required = True)
parser.add_argument('-d', "--delay-file", help="Path to the file that specifies delays: each line must be <agent;(x,y);(x,y);delayed_start_time> for delays that must be handled sequentially.", required=True, default=None)
parser.add_argument('-e', "--end-time", help="End time of the scenario, if None is given", required=False, default=None)

def run_flexsipp(location_file, scenario_file, delay_agent_id, scenario_end):
    if delay_agent_id is None:
        delay_agent_id = 1
    else:
        delay_agent_id = int(delay_agent_id)
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end, delay_agent_id)
    assert delay_agent_id in agents, f"ERROR: no delay agent with id {delay_agent_id} in the set of agents."
    delay_agent = agents[delay_agent_id]
    # Heuristic for delay agent
    heuristic = graph.calculate_heuristic(delay_agent.destination)
    flexSIPP = FSIPP(graph, heuristic, len(agents))
    result = flexSIPP.run_search(1000, delay_agent.origin.name, delay_agent.destination.name, 0)
    print(result)

    fig, axs = plt.subplots(1,2, figsize = (10,5))
    result.plot(axs[0], linestyle=3)
    axs[0].set_xlabel('Departure Time')
    axs[0].set_ylabel('Arrival Time')
    axs[0].set_title('Arrival time function')

    axs[1].grid(alpha=0.3)
    delay_agent.plot_route(axs[1])
    axs[1].set_ylim(0, graph.global_end_time)
    axs[1].set_xlabel('Location')
    axs[1].set_ylabel('Time')
    axs[1].set_title('Unsafe Intervals')
    plt.show()
    plt.close()

def repeated_delays(location_file, scenario_file, delay_file, scenario_end):
    timeout = 300
    graph, agents, unsafe_intervals = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end, None)
    delays = parse_delays(delay_file, graph)
    updates = []
    for delay_agent_id, origin, destination, start_time, actual_delay in delays:
        assert delay_agent_id in agents, f"ERROR: no delay agent with id {delay_agent_id} in the set of agents."
        delay_agent = agents[delay_agent_id]
        for node_or_edge in unsafe_intervals[delay_agent_id]:
            for interval in unsafe_intervals[delay_agent_id][node_or_edge]:
                node_or_edge.remove_unsafe_interval(interval)
        print(f"Need to find a new path for agent {delay_agent_id} from {origin} to {destination} starting at {start_time} with delay {actual_delay}")
        heuristic = graph.calculate_heuristic(delay_agent.destination)
        flexSIPP = FSIPP(graph, heuristic, len(agents))
        result = flexSIPP.run_search(timeout, origin, destination, start_time)
        new_path = result.get_fastest_route(actual_delay)
        print(f"Found new path for agent {delay_agent_id}: {new_path}")
        update_unsafe_intervals(graph, unsafe_intervals, new_path, delay_agent, actual_delay)
        updates.append((delay_agent, (origin, destination, start_time, actual_delay), new_path))
        # for node_or_edge in unsafe_intervals[delay_agent_id]:
        #     print("Old", node_or_edge, unsafe_intervals[delay_agent_id][node_or_edge])
        #     print("New", node_or_edge, updated_unsafe_intervals[delay_agent_id][node_or_edge])
    for upd in updates:
        print(f"Agent {upd[0]} was delayed at {upd[1][0]} for {upd[1][-1]} and found a new path: {[x[0].name for x in upd[2][1]["route"]]}")

def update_unsafe_intervals(graph, unsafe_intervals, new_path, delay_agent, actual_delay):
    # The unsafe intervals were never compiled onto the nodes and edges because this is the delayed agent, so we only update the unsafe intervals in our global list to use them in the next iteration
    print(delay_agent.route)
    print(new_path[1]["route"])
    update_route = False
    old_intervals = {}
    for node_or_edge in delay_agent.route:
        if isinstance(node_or_edge, Node) and node_or_edge in new_path[1]["route"][0]:
            update_route = True
        if update_route:
            old_intervals[node_or_edge] = unsafe_intervals[delay_agent.id][node_or_edge]
            unsafe_intervals[delay_agent.id][node_or_edge] = []
        if isinstance(node_or_edge, Node) and node_or_edge in new_path[1]["route"][-1]:
            update_route = False
    delay_origin, used_safe_interval = new_path[1]["route"][0]
    unsafe_interval = get_matching_unsafe_interval(old_intervals, delay_origin, used_safe_interval, delay_agent)
    unsafe_interval.end += actual_delay
    unsafe_intervals[delay_agent.id][delay_origin] = [unsafe_interval]
    print(f"Add delay {actual_delay} to update interval: {unsafe_interval}")
    for i in range(1, len(new_path[1]["route"])):
        # TODO use edges from route
        from_node, used_safe_interval_from_node = new_path[1]["route"][i-1]
        to_node, used_safe_interval_to_node = new_path[1]["route"][i]
        unsafe_interval = get_matching_unsafe_interval(old_intervals, to_node, used_safe_interval_to_node, delay_agent)
        # TODO what if interval is not found
        if unsafe_interval is not None:
            if unsafe_interval.duration == 1:
                unsafe_interval.start += actual_delay
                unsafe_interval.end += actual_delay
            else:
                unsafe_interval.start += actual_delay
                unsafe_interval.end += (actual_delay - interval.duration)
            unsafe_interval.end = min(unsafe_interval.end, graph.global_end_time)
            print(f"Add delay {actual_delay} to update interval: {unsafe_interval} on node {to_node}")
            unsafe_intervals[delay_agent.id][to_node] = [unsafe_interval]

        edge_interval = None
        edge_used = None
        for edge in from_node.outgoing:
            if edge.to_node == to_node:
                edge_used = edge
                for interval in old_intervals[edge]:
                    if interval.start > used_safe_interval_from_node[0] and interval.start < used_safe_interval_from_node[1] \
                        and interval.end >= used_safe_interval_to_node[0] and interval.end <= used_safe_interval_to_node[1]:
                            assert interval.by_agent == delay_agent
                            edge_interval = interval
                            break
        if edge_interval is not None:
            edge_interval.start += actual_delay
            edge_interval.end += actual_delay
            unsafe_intervals[delay_agent.id][edge_used] = [edge_interval]
            unsafe_intervals[delay_agent.id][edge_used.opposite] = [edge_interval]
            print(f"Add delay {actual_delay} to update interval: {edge_interval} on edge {edge_used} and opposite {edge.opposite}")
    return unsafe_intervals
        
def get_matching_unsafe_interval(unsafe_intervals, node_or_edge, safe_interval_to_match, delay_agent):
    # Get the interval that fits into the safe interval used
    for interval in unsafe_intervals[node_or_edge]:
        print(node_or_edge, interval, safe_interval_to_match)
        if interval.start > safe_interval_to_match[0] and interval.end <= safe_interval_to_match[1]:
            assert interval.by_agent == delay_agent
            return interval
    return None
        
    
def parse_delays(delay_file, grid):
    delays = []
    with open(delay_file, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=';', quotechar='|')
        fields = next(reader)
        for row in reader:
            # In the MAPF examples, the nodes are given as '(y,x)' coordinates
            origin = f"({row[1].split(',')[1].replace(')', '')},{row[1].split(',')[0].replace('(', '')})"
            destination = f"({row[2].split(',')[1].replace(')', '')},{row[2].split(',')[0].replace('(', '')})"
            delays.append((int(row[0]), origin, destination, float(row[3]), float(row[4])))
    return delays

if __name__ == "__main__":
    args = parser.parse_args()
    repeated_delays(args.location_file, args.scenario_file, args.delay_file, args.end_time)
