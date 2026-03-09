import argparse
import csv

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

def repeated_delays(location_file, scenario_file, delay_file, scenario_end):
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    delays = parse_delays(delay_file, graph)
    fig, axs = plt.subplots(1, 2 * len(delays), figsize=(5 * len(delays), 5))
    x = 0
    for delay_agent_id, origin, destination, start_time, actual_delay in delays:
        # Get the agent that requires replanning
        assert delay_agent_id in agents, f"ERROR: no delay agent with id {delay_agent_id} in the set of agents."
        delay_agent = agents[delay_agent_id]

        # Plot the route of the delay_agent
        ax = axs[x]
        ax.set_ylim((0, graph.global_end_time))
        ax.grid(alpha=0.3)
        ax.set_yticks(range(0, 20))
        delay_agent.plot_route(ax)

        # Filter out that agents unsafe intervals
        graph.filter_out_agent(delay_agent)

        # Pre calculate the heuristic
        heuristic = graph.calculate_heuristic(delay_agent.destination)

        # Create safe intervals and calculate the ATFs
        flexSIPP = FSIPP(graph, heuristic, agents)
        # Run the expansion A* search
        result = flexSIPP.run_search(origin, destination, start_time)
        print(result)

        # Pick a route from the results the agent will take, currently selecting a given amount of delay
        atf, new_route, minimum_delays = result.get_fastest_route(actual_delay, agents, discrete=True)

        # Update the unsafe intervals such that it can be used again
        del minimum_delays[delay_agent]
        graph.update_unsafe_intervals(new_path=(delay_agent, new_route, actual_delay), minimum_delays=minimum_delays)

        # Plot the route of the delay_agent after updating
        ax = axs[x + 1]
        ax.set_ylim((0, graph.global_end_time))
        ax.grid(alpha=0.3)
        ax.set_yticks(range(0, 20))
        delay_agent.plot_route(ax)
        x+=2
    plt.show()
    plt.close()
    
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
    # Run with data/mapf/corridor/
    args = parser.parse_args()
    repeated_delays(args.location_file, args.scenario_file, args.delay_file, args.end_time)
