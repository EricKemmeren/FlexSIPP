import argparse

from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from numpy.ma.core import minimum

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

    # Agent 1 (top left) breaks down, and is unable to move from (0,0)
    graph.filter_out_agent(agents[1])
    graph.nodes["(0,0)"].add_unsafe_interval(UnsafeInterval(0.1, graph.global_end_time, 0, agents[1], 0))

    # The route of Agent 2 is not not possible anymore, we should find a new route for this agent
    rerouting_agent = agents[2]
    for agent in agents.values():
        agent.max_buffer = 5

    # Filter out it's unsafe intervals because it will find a new route
    graph.filter_out_agent(rerouting_agent)

    continues = False
    actual_departure_time = 1
    start_time = 0
    show_buffer_time = True

    # Don't use a heuristic, set it to 0 for every node
    heuristic = {node.name: 0 for node in graph.nodes.values()}
    flexSIPP = FSIPP(graph, heuristic, agents)
    result = flexSIPP.run_search(graph.global_end_time, rerouting_agent.origin.name, rerouting_agent.destination.name, start_time)
    print(result)

    fig, axs = plt.subplots(2,3, figsize = (15,10))
    result.plot(axs[0,0], linestyle=3)
    axs[1,0].grid(alpha=0.3)
    result.plot(axs[1,0], show_atf=False, show_additional_delays=True, show_total_delays=True, original_arrival_time=3)

    custom_lines = [Line2D([0], [0], color="blue"),
                    Line2D([0], [0], color="lightblue"),]
    axs[1,0].legend(custom_lines, ["Total delay", "Other agents delay"])
    tipping_points = result.find_tipping_points(original_arrival_time=3, optimize_total_delay=False)
    for tipping_point in tipping_points:
        atf, new_route, minimum_delays = result.get_fastest_route(tipping_point, agents, beta_inclusive=True)
        for agent, delays in minimum_delays.items():
            if delays:
                print(f"Tipping point for agent {agent} at {list(delays.keys())[0]}, {tipping_point}")

    ax = axs[0,1]
    ax.grid(alpha=0.3)
    rerouting_agent.plot_route(ax, continues=continues, title="Unsafe interval on original path", show_buffer_time=show_buffer_time)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    ax = axs[1,1]
    ax.grid(alpha=0.3)
    agents[4].plot_route(ax, continues=continues, title="Agent 4 before", show_buffer_time=show_buffer_time)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    # Update the graph with the results from flexsipp, assume we now know the actual delay of the agent
    atf, new_route, minimum_delays = result.get_fastest_route(actual_departure_time, agents)
    del minimum_delays[rerouting_agent]
    graph.update_unsafe_intervals(new_path=(rerouting_agent, new_route, actual_departure_time), minimum_delays=minimum_delays)

    # TODO: check flexibility creation, possibly an error here.
    graph.reset_flexibility()
    for agent in agents.values():
        agent.calculate_flexibility()

    ax = axs[0,2]
    ax.grid(alpha=0.3)
    rerouting_agent.plot_route(ax, continues=continues, title=f"Unsafe Intervals when departing at {actual_departure_time}", show_buffer_time=False)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    ax = axs[1,2]
    ax.grid(alpha=0.3)
    agents[4].plot_route(ax, continues=continues, title="Agent 4 after", show_buffer_time=False)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    plt.show()
    plt.close()


if __name__ == "__main__":
    args = parser.parse_args()
    run_flexsipp(args.location_file, args.scenario_file, args.delay_agent, args.end_time)
