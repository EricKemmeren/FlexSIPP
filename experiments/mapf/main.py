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
    for route in result.unique_path_eatfs:
        for atf in result.unique_path_eatfs[route]:
            print(f"Found route with atf", atf, route)

    fig, axs = plt.subplots(1,3, figsize = (15,5))
    result.plot(axs[0], linestyle=3)

    axs[1].grid(alpha=0.3)
    delay_agent.plot_route(axs[1])
    axs[1].set_ylim(0, graph.global_end_time)

    atf, new_route, minimum_delays = result.get_fastest_route(float(actual_delay), agents, discrete=True)
    if new_route:
        del minimum_delays[delay_agent]
        graph.update_unsafe_intervals(minimum_delays=minimum_delays)

    delay_agent.plot_route(axs[2])

    tipping_points = result.find_tipping_points(original_arrival_time=original_arrival_time, optimize_total_delay=False)
    for tipping_point in tipping_points:
        atf, new_route, minimum_delays = result.get_fastest_route(tipping_point, agents, beta_inclusive=True)
        for agent, delays in minimum_delays.items():
            if delays:
                print(f"Tipping point for agent {agent} at {list(delays.keys())[0]}, {tipping_point}")

    plt.show()
    plt.close()


def corridor_example():
    scenario_end = 20
    delay_agent_id = 1
    location_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", "corridor", "corridor.map")
    scenario_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", "corridor", "corridor-2agnets_paths.txt")

    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    delay_agent = agents[delay_agent_id]
    graph.filter_out_agent(delay_agent)
    # Heuristic for delay agent
    heuristic = graph.calculate_heuristic(delay_agent.destination)
    flexSIPP = FSIPP(graph, heuristic, agents)
    result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, 0)

    fig, axs = plt.subplots(1,3, figsize = (15,5))
    result.plot(axs[0], linestyle=3)

    axs[1].grid(alpha=0.3)
    delay_agent.plot_route(axs[1])
    axs[1].set_ylim(0, graph.global_end_time)

    min_delay = 1
    atf, new_route, minimum_delays = result.get_fastest_route(1, agents, discrete=True)
    del minimum_delays[delay_agent]
    graph.update_unsafe_intervals(minimum_delays=minimum_delays)

    delay_agent.plot_route(axs[1])

    flexSIPP = FSIPP(graph, heuristic, agents)
    result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, 6)

    atf, new_route, minimum_delays = result.get_fastest_route(10, agents, discrete=True)
    del minimum_delays[delay_agent]
    graph.update_unsafe_intervals(minimum_delays=minimum_delays)

    delay_agent.plot_route(axs[1])
    result.plot(axs[2], linestyle=3)

    plt.show()
    plt.close()

if __name__ == "__main__":
    # Run with data/mapf/corridor
    args = parser.parse_args()
    run_flexsipp(args.location_file, args.scenario_file, args.delay_agent, args.end_time, args.actual_delay)
    # corridor_example()
