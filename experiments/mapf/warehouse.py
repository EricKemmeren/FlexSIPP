import argparse

from matplotlib import pyplot as plt

from experiments.mapf.agent import MapfAgent
from flexsipp.graphs.fsipp import FSIPP
from flexsipp.util.intervals import UnsafeInterval
from read_experiment import create_mapf_instance_from_paths

parser = argparse.ArgumentParser(
                    prog='FlexSIPP',
                    description='Given a location (file) and a scenario (file), run the FlexSIPP program')
parser.add_argument('-l', "--location-file", help = "Path to the location file", required = True)
parser.add_argument('-s', "--scenario-file", help = "Path to the scenario file", required = True)
parser.add_argument('-a', "--delay-agent", help="Identifier (int) of the agent in the scenario_file that is delayed. If not specified, the first agent in the scenario wil be chosen.", required=False, default=None)
parser.add_argument('-e', "--end-time", help="End time of the scenario, if None is given", required=False, default=None)

def run_flexsipp(location_file, scenario_file, delay_agent_id, scenario_end):
    if delay_agent_id is None:
        delay_agent_id = 1
    else:
        delay_agent_id = int(delay_agent_id)
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    assert delay_agent_id in agents, f"ERROR: no delay agent with id {delay_agent_id} in the set of agents."
    delay_agent = agents[delay_agent_id]
    for agent in agents.values():
        agent.max_buffer = 2

    graph.filter_out_agent(delay_agent)

    # obstacle = MapfAgent(2, [], graph.global_end_time)
    # obstacle.max_buffer = 0
    # agents[obstacle.id] = obstacle
    # graph.nodes["(2,0)"].add_unsafe_interval(UnsafeInterval(3, 10, 1, obstacle, 0))
    # Heuristic for delay agent
    heuristic = graph.calculate_heuristic(delay_agent.destination)
    flexSIPP = FSIPP(graph, heuristic, agents)
    result = flexSIPP.run_search(1000, delay_agent.origin.name, delay_agent.destination.name, 0)
    print(result)

    fig, axs = plt.subplots(1,3, figsize = (15,5))
    result.plot(axs[0], linestyle=3)

    axs[1].grid(alpha=0.3)
    delay_agent.plot_route(axs[1], continues=True)
    axs[1].set_ylim(0, graph.global_end_time)
    axs[1].set_yticks(range(0, graph.global_end_time + 1, 2))

    atf, new_route, minimum_delays = result.get_fastest_route(1, agents, discrete=True)
    del minimum_delays[delay_agent]
    graph.update_unsafe_intervals(minimum_delays=minimum_delays)

    delay_agent.plot_route(axs[1])

    plt.show()
    plt.close()


if __name__ == "__main__":
    args = parser.parse_args()
    run_flexsipp(args.location_file, args.scenario_file, args.delay_agent, args.end_time)
