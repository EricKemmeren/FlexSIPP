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

from agent import MapfAgent
from flexsipp.graphs.fsipp import FSIPP
from flexsipp.util.intervals import UnsafeInterval
from read_experiment import create_mapf_instance_from_paths

import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

def run_flexsipp(location_file, scenario_file):
    end_time = 12
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, end_time)

    # Agent 1 (top left) breaks down, and is unable to move from (0,0)
    broken_down_agent = agents[1]
    original_arrival_time_breakdown = broken_down_agent.destination.unsafe_intervals[-1].start
    graph.filter_out_agent(broken_down_agent)
    graph.nodes["(0,0)"].add_unsafe_interval(UnsafeInterval(0.1, graph.global_end_time, 0, broken_down_agent, 0))

    # The route of Agent 2 is not not possible anymore, we should find a new route for this agent
    rerouting_agent = agents[2]
    for agent in agents.values():
        agent.max_buffer = 5
    original_arrival_time_reroute = rerouting_agent.destination.unsafe_intervals[-1].start

    # Filter out unsafe intervals of Agent 2 because it will find a new route
    graph.filter_out_agent(rerouting_agent)
    
    # Agent 4 has feasibility
    feasibility_agent = agents[4]

    continues = False
    actual_departure_time = 0
    start_time = 0
    show_buffer_time = True

    # Don't use a heuristic, set it to 0 for every node
    heuristic = {node.name: 0 for node in graph.nodes.values()}

    flexSIPP = FSIPP(graph, heuristic, agents)
    result = flexSIPP.run_search(rerouting_agent.origin.name, rerouting_agent.destination.name, start_time, graph.global_end_time)
    print(f"FlexSIPP Search time (python) {result.metadata["Search Time Python"]:.2f}, (c++) {result.metadata["Search Time"]} yields: ", result)

    fig, axs = plt.subplots(2,4, figsize = (15,10))
    result.plot(axs[0,0], linestyle=3)
    axs[1,0].grid(alpha=0.3)
    result.plot(axs[1,0], show_atf=False, show_additional_delays=True, show_total_delays=True, original_arrival_time=original_arrival_time_reroute)

    custom_lines = [Line2D([0], [0], color="blue"),
                    Line2D([0], [0], color="lightblue"),]
    axs[1,0].legend(custom_lines, ["Total delay", "Other agents delay"], title="Objective", loc="lower right")
    tipping_points = result.find_tipping_points(original_arrival_time=original_arrival_time_reroute, optimize_total_delay=False)
    for tipping_point in tipping_points:
        atf, new_route, minimum_delays = result.get_fastest_route(tipping_point, agents, beta_inclusive=True)
        for agent, delays in minimum_delays.items():
            if delays:
                print(f"Tipping point for agent {agent} at {list(delays.keys())[0]}, {tipping_point}")
    
    found_flexibility_ranges = result.plot(axs[1,0], show_atf=False, show_additional_delays=True)
    create_paper_plot(result, found_flexibility_ranges, graph.global_end_time)

    ax = axs[0,1]
    ax.grid(alpha=0.3)
    rerouting_agent.plot_route(ax, continues=continues, title="Unsafe interval on original path", show_buffer_time=show_buffer_time)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    ax = axs[1,1]
    ax.grid(alpha=0.3)
    feasibility_agent.plot_route(ax, continues=continues, title="Agent 4 before", show_buffer_time=show_buffer_time)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    # Update the graph with the results from FlexSIPP, assume we know now the actual delay of Agent 2
    atf, new_route, minimum_delays = result.get_fastest_route(actual_departure_time, agents, discrete=True)
    del minimum_delays[rerouting_agent]
    graph.update_unsafe_intervals(new_path=(rerouting_agent, new_route, actual_departure_time), minimum_delays=minimum_delays)

    graph.reset_flexibility()
    for agent in agents.values():
        agent.calculate_flexibility()

    ax = axs[0,2]
    ax.grid(alpha=0.3)
    rerouting_agent.plot_route(ax, continues=continues, title=f"Unsafe Intervals Agent {rerouting_agent.id} when departing at {actual_departure_time}", show_buffer_time=True)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    ax = axs[1,2]
    ax.grid(alpha=0.3)
    feasibility_agent.plot_route(ax, continues=continues, title="Agent 4 after", show_buffer_time=True)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    # Now set agent 1 to available again
    restart_time = 3
    print(f"Now restarting agent {broken_down_agent.id} at {restart_time}")
    graph.nodes["(0,0)"].unsafe_intervals.remove(UnsafeInterval(0.1, graph.global_end_time, 0, broken_down_agent, 0))
    graph.nodes["(0,0)"].add_unsafe_interval(UnsafeInterval(0.1, restart_time, 0, broken_down_agent, 0))
    flexSIPP = FSIPP(graph, heuristic, agents)
    update_result = flexSIPP.run_search(broken_down_agent.origin.name, broken_down_agent.destination.name, restart_time, graph.global_end_time)
    print(f"FlexSIPP agent {broken_down_agent.id} Search time {result.metadata["Search Time Python"]:.2f} yields: ", update_result,)

    update_result.plot(axs[0,3], linestyle=3)
    axs[1,3].grid(alpha=0.3)
    update_result.plot(axs[1,3], show_atf=False, show_additional_delays=True, show_total_delays=True, original_arrival_time=original_arrival_time_breakdown)

    custom_lines = [Line2D([0], [0], color="blue"),
                    Line2D([0], [0], color="lightblue"),]
    axs[1,3].legend(custom_lines, ["Total delay", "Other agents delay"], title="Objective", loc="lower right")
    tipping_points = update_result.find_tipping_points(original_arrival_time=original_arrival_time_breakdown, optimize_total_delay=False)
    for tipping_point in tipping_points:
        atf, new_route, minimum_delays = update_result.get_fastest_route(tipping_point, agents, beta_inclusive=True)
        for agent, delays in minimum_delays.items():
            if delays:
                print(f"Tipping point for agent {agent} at {list(delays.keys())[0]}, {tipping_point}")
    plt.show()
    plt.close()
                
def create_paper_plot(result, flexibility_used, end_time):
    flexibility = []
    for start, end in flexibility_used:
        if not flexibility:
            flexibility.append((start,end))
        elif flexibility[-1][0] == end:
            flexibility[-1] = (start, flexibility[-1][1])
        elif flexibility[-1][1] == start:
            flexibility[-1] = (flexibility[-1][0], end)

    matplotlib.rcParams["font.size"] = 12
    figure = plt.figure(figsize=(4,2.3))
    ax = figure.add_axes((0.12,0.2,0.85,0.75))
    ax.set_xlabel('Departure Time')
    ax.set_ylabel('Arrival Time')
    lines = {
        "flexible": {
            "linestyle": result.linestyles[3],
            "color": "red"
        },
        "regular": {
            "linestyle": result.linestyles[0],
            "color": "blue"
        }
    }
    for (x0, x1, y0, y1) in result.segments:
        line_type = None
        for ((s, e), (delta_alpha, delta_beta)) in flexibility_used:
            if x0 >= s and x1 <= e and delta_alpha > 0:
                line_type = "flexible"
                break
        if not line_type:
            line_type = "regular"
        if x0 == "-inf" and x1 != "inf" and y1 != "inf":
            ax.hlines(float(y1), 0, float(x1), color=lines[line_type]["color"], linestyle=lines[line_type]["linestyle"])
        ax.plot([float(x0), float(x1)], [float(y0), float(y1)], 
                        color=lines[line_type]["color"], linestyle=lines[line_type]["linestyle"], label=line_type)
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = OrderedDict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), title="Found path")
    plt.savefig(os.path.join(os.path.dirname(__file__), "output", "warehouse.pdf"))
    plt.close()


if __name__ == "__main__":
    location = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", "warehouse", "warehouse.map")
    paths = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", "warehouse", "paths.txt")
    run_flexsipp(location, paths)
