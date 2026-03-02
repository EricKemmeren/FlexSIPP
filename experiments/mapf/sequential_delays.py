import argparse

from matplotlib import pyplot as plt

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
    heuristic = {node.name: graph.calculate_heuristic(delay_agent.route[-1], 1) for node in graph.nodes.values()}
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
    for delay_agent_id, origin, destination, start_time in delays:
        assert delay_agent_id in agents, f"ERROR: no delay agent with id {delay_agent_id} in the set of agents."
        delay_agent = agents[delay_agent_id]
        heuristic = {node.name: graph.calculate_heuristic(delay_agent.destination, 1) for node in graph.nodes.values()}
        flexSIPP = FSIPP(graph, heuristic, len(agents))
        result = flexSIPP.run_search(timeout, origin, destination, start_time)
        print(result)
    
def parse_delays(delay_file, grid):
    with open(delay_file, "r") as f:
        lines = f.readlines()
        delays = []
        for line in lines:
            # Each line should be formatted as {agent_id;(y,x);(y,x);delay_start_time}
            parts = line.strip().split(";")
            origin = f"({parts[1].split(',')[1].replace(')', '')},{parts[1].split(',')[0].replace('(', '')})"
            destination = f"({parts[2].split(',')[1].replace(')', '')},{parts[2].split(',')[0].replace('(', '')})"
            delays.append((int(parts[0]), origin, destination, float(parts[3])))
        print(delays)
        return delays

if __name__ == "__main__":
    args = parser.parse_args()
    repeated_delays(args.location_file, args.scenario_file, args.delay_file, args.end_time)
