import os
import argparse

from matplotlib import pyplot as plt

from flexsipp.graphs.fsipp import FSIPP
from read_experiment import create_mapf_instance_from_paths

import logging
logger = logging.getLogger()

parser = argparse.ArgumentParser(
                    prog='FlexSIPP',
                    description='Given a location (file) and a scenario (file), run the FlexSIPP program')
parser.add_argument('-l', "--location-file", help = "Path to the location file", required = True)
parser.add_argument('-s', "--scenario-file", help = "Path to the scenario file", required = True)
parser.add_argument('-d', "--delay-agent", help="Identifier (int) of the agent in the scenario_file that is delayed. If not specified, the first agent in the scenario wil be chosen.", required=False, default=None)
parser.add_argument('-e', "--end-time", help="End time of the scenario, if None is given", required=False, default=None)
parser.add_argument('-a', "--actual-delay", help="Actual delayed start time of the delayed agent, used to get the fastest route, assumed to be 1", required=False, default=1)

def run_flexsipp(location_file, scenario_file, delay_agent_id, scenario_end, actual_delay):
    if delay_agent_id is None:
        delay_agent_id = 1
    else:
        delay_agent_id = int(delay_agent_id)
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    assert delay_agent_id in agents, f"ERROR: no delay agent with id {delay_agent_id} in the set of agents."
    delay_agent = agents[delay_agent_id]
    original_arrival_time = delay_agent.destination.unsafe_intervals[-1].start
    graph.filter_out_agent(delay_agent)
    # Heuristic for delay agent
    heuristic = graph.calculate_heuristic(delay_agent.destination)
    flexSIPP = FSIPP(graph, heuristic, agents)
    result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, 0)
    for route in result.unique_routes:
        for atf in result.unique_routes_eatfs[route]:
            print(f"Found route with atf", atf, route)

    fig, axs = plt.subplots(1,3, figsize = (15,5))
    result.plot(axs[0], linestyle=3)

    axs[1].grid(alpha=0.3)
    delay_agent.plot_route(axs[1])
    axs[1].set_ylim(0, graph.global_end_time)

    atf, new_route, minimum_delays, _ = result.get_fastest_route(float(actual_delay), agents, discrete=True)
    if new_route:
        del minimum_delays[delay_agent]
        graph.update_unsafe_intervals(minimum_delays=minimum_delays)

    delay_agent.plot_route(axs[2])

    tipping_points = result.find_tipping_points(agents, original_arrival_time=original_arrival_time, optimize_total_delay=False)
    optimal_start_times = result.find_tipping_points(agents, original_arrival_time=original_arrival_time, optimize_total_delay=True)
    
    plt.show()
    plt.close()

if __name__ == "__main__":
    # Run with data/mapf/corridor
    args = parser.parse_args()
    run_flexsipp(args.location_file, args.scenario_file, args.delay_agent, args.end_time, args.actual_delay)
