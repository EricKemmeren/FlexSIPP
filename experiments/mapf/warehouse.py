import os
from collections import OrderedDict
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
import shutil

if shutil.which('pdflatex'):
    from matplotlib.backends.backend_pgf import FigureCanvasPgf
    matplotlib.backend_bases.register_backend('pdf', FigureCanvasPgf)
    matplotlib.rcParams.update({
        "pgf.texsystem": "pdflatex",
        'pgf.rcfonts': False,
    })

from flexsipp_mapf.agent import MapfAgent
from flexsipp.graphs.fsipp import FSIPP
from flexsipp.util.intervals import UnsafeInterval
from read_experiment import create_mapf_instance_from_paths

import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

def run_flexsipp_scenario(location_file, scenario_file):
    end_time = 12
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, end_time)

    # Agent 1 (top left) breaks down, and is unable to move from (0,0)
    broken_down_agent = agents[1]
    original_arrival_time_breakdown = broken_down_agent.destination.unsafe_intervals[-1].start
    graph.filter_out_agent(broken_down_agent)
    graph.nodes["(0,0)"].add_unsafe_interval(UnsafeInterval(0.1, graph.global_end_time, 0, broken_down_agent, 0))
    graph.nodes["(0,0)"].merge_unsafe_intervals()

    # The route of Agent 2 is not not possible anymore, we should find a new route for this agent
    rerouting_agent = agents[2]
    original_arrival_time_reroute = rerouting_agent.destination.unsafe_intervals[-1].start

    # Filter out unsafe intervals of Agent 2 because it will find a new route
    graph.filter_out_agent(rerouting_agent)
    
    # Agent 4 has flexibility
    flexibility_agent = agents[4]

    continues = False
    actual_departure_time = 3
    start_time = 0
    show_buffer_time = True

    # Don't use a heuristic, set it to 0 for every node
    heuristic = {node.name: 0 for node in graph.nodes.values()}

    flexSIPP = FSIPP(graph, heuristic, agents)
    result = flexSIPP.run_search(rerouting_agent.origin.name, rerouting_agent.destination.name, start_time, graph.global_end_time, optimize_total_delay=False, redirect_stderr="stderr_warehouse.txt")
    print(f"FlexSIPP Search time (python) {result.metadata["Search Time Python"]:.2f}, (c++) {result.metadata["Search Time"]} yields: ", result)

    fig, axs = plt.subplots(2, 4, figsize = (15,10))
    result.plot(axs[0,0], linestyle=3)
    axs[1,0].grid(alpha=0.3)
    result.plot(axs[1,0], show_atf=False, show_additional_delays=True, show_total_delays=True, original_arrival_time=original_arrival_time_reroute)

    custom_lines = [Line2D([0], [0], color="blue"),
                    Line2D([0], [0], color="lightblue"),]
    axs[1,0].legend(custom_lines, ["Total delay", "Other agents delay"], title="Objective", loc="lower right")

    tipping_points = result.find_tipping_points(agents, original_arrival_time=original_arrival_time_reroute, optimize_total_delay=False, print_tipping_points=True, plot_on_axis=axs[1,0])
    optimal_start_time = result.find_tipping_points(agents, original_arrival_time=original_arrival_time_reroute, optimize_total_delay=True, print_tipping_points=True, plot_on_axis=axs[1,0])
    
    found_flexibility_ranges = result.plot(axs[1,0], show_atf=False, show_additional_delays=True)

    ax = axs[1,1]
    ax.grid(alpha=0.3)
    flexibility_agent.plot_route(ax, continues=continues, title=f"Agent {flexibility_agent} before", show_buffer_time=show_buffer_time)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    # Update the graph with the results from FlexSIPP, assume we know now the actual delay of Agent 2
    atf, new_route, minimum_delays = result.get_fastest_route(actual_departure_time, agents, discrete=False)

    ax = axs[0,1]
    ax.grid(alpha=0.3)
    temp_agent = MapfAgent(0, [node for node, interval in graph._complete_new_route(new_route)], graph.global_end_time)
    temp_agent.plot_route(ax, continues=continues, title="Original unsafe interval on found path", show_buffer_time=show_buffer_time)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    del minimum_delays[rerouting_agent]
    graph.update_unsafe_intervals(new_path=(rerouting_agent, new_route, actual_departure_time), minimum_delays=minimum_delays)

    ax = axs[0,2]
    ax.grid(alpha=0.3)
    rerouting_agent.plot_route(ax, continues=continues, title=f"Unsafe Intervals Agent {rerouting_agent.id} when departing at {actual_departure_time}", show_buffer_time=True)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    ax = axs[1,2]
    ax.grid(alpha=0.3)
    flexibility_agent.plot_route(ax, continues=continues, title="Agent 4 after", show_buffer_time=True)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    # Now set agent 1 to available again
    restart_time = 2
    new_goal = "(3,1)"
    print(f"Now restarting agent {broken_down_agent.id} at {restart_time}")
    graph.nodes["(0,0)"].unsafe_intervals.remove(UnsafeInterval(0.1, graph.global_end_time, 0, broken_down_agent, 0))
    graph.nodes["(0,0)"].add_unsafe_interval(UnsafeInterval(0.1, restart_time, 0, broken_down_agent, 0))
    graph.nodes["(0,0)"].merge_unsafe_intervals()
    flexSIPP = FSIPP(graph, heuristic, agents)
    update_result = flexSIPP.run_search(broken_down_agent.origin.name, new_goal, restart_time, graph.global_end_time)
    print(f"FlexSIPP agent {broken_down_agent.id} Search time {result.metadata["Search Time Python"]:.2f} yields: ", update_result,)

    update_result.plot(axs[0,3], linestyle=3)
    axs[1,3].grid(alpha=0.3)
    update_result.plot(axs[1,3], show_atf=False, show_additional_delays=True, show_total_delays=True, original_arrival_time=original_arrival_time_breakdown)

    custom_lines = [Line2D([0], [0], color="blue"),
                    Line2D([0], [0], color="lightblue"),]
    axs[1,3].legend(custom_lines, ["Total delay", "Other agents delay"], title="Objective", loc="lower right")

    tipping_points = update_result.find_tipping_points(agents, original_arrival_time=original_arrival_time_breakdown, optimize_total_delay=False)

    plt.show()
    plt.close()


if __name__ == "__main__":
    location = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", "example_warehouse", "warehouse.map")
    paths = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", "example_warehouse", "paths.txt")
    run_flexsipp_scenario(location, paths)
