import os
from collections import OrderedDict
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
import shutil

from flexsipp.graphs.graph import Node

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

    # TODO when not using the to-node interval on edge intervals: agent 2 should end in (2,6) to include other path.
    # Set some initial buffer time
    for agent in agents.values():
        agent.max_buffer = 5

    # Agent 1 is delayed
    rerouting_agent = agents[1]
    original_arrival_time_reroute = rerouting_agent.destination.unsafe_intervals[-1].start

    # Filter out unsafe intervals of Agent 1 because it will find a new route
    graph.filter_out_agent(rerouting_agent)
    
    # Agent 2 has flexibility
    flexibility_agent = agents[2]

    start_time = 0
    continues = False
    show_buffer_time = True
    
    # for x, node in graph.nodes.items():
    #     print(f"Node {x} has unsafe intervals {' '.join([f'A{ui.by_agent}: <{ui.start},{ui.end}> [{ui.duration}] recovery {ui.local_recovery_time}'for ui in node.unsafe_intervals])}")
    # for move in flexibility_agent.route:
    #     print(f"-unsafe- {move} {' '.join([f'A{ui.by_agent}: <{ui.start},{ui.end}> [{ui.duration}]'for ui in move.unsafe_intervals])}")
        # for edge in graph.nodes[node].outgoing:
        #     print(f"-unsafe- edge {edge} {edge.unsafe_intervals}")

    # Don't use a heuristic, set it to 0 for every node
    heuristic = {node.name: 0 for node in graph.nodes.values()}

    flexSIPP = FSIPP(graph, heuristic, agents, use_flexibility=True)
    flexSIPP._write(open(os.path.join(os.path.dirname(__file__), "output", "warehouse_delay_graph_FlexSIPP.txt"), "w"))
    result = flexSIPP.run_search(rerouting_agent.origin.name, rerouting_agent.destination.name, start_time, graph.global_end_time, optimize_total_delay=False, redirect_stderr="stderr_warehouse_FlexSIPP.txt")
    print(f"FlexSIPP Search time (python) {result.metadata['Search Time Python']:.2f}, (c++) {result.metadata['Search Time']} yields: ", result)

    fig, axs = plt.subplots(2, 4, figsize = (15,10))
    result.plot(axs[0,0], linestyle=3)
    axs[1,0].grid(alpha=0.3)
    result.plot(axs[1,0], show_atf=False, show_additional_delays=True, show_total_delays=True, original_arrival_time=original_arrival_time_reroute, rerouted_agent=rerouting_agent.id)

    custom_lines = [Line2D([0], [0], color="blue"),
                    Line2D([0], [0], color="lightblue"),]
    axs[1,0].legend(custom_lines, ["Total delay", "Other agents delay"], title="Objective", loc="lower right")

    maeder = FSIPP(graph, heuristic, agents, use_flexibility=False)
    result_maeder = maeder.run_search(rerouting_agent.origin.name, rerouting_agent.destination.name, start_time, graph.global_end_time, optimize_total_delay=False, redirect_stderr="stderr_warehouse_maeder.txt")

    tipping_points = result.find_tipping_points(agents, original_arrival_time=original_arrival_time_reroute, optimize_total_delay=False, print_tipping_points=True, plot_on_axis=axs[1,0])
    optimal_start_time = result.find_tipping_points(agents, original_arrival_time=original_arrival_time_reroute, optimize_total_delay=True, print_tipping_points=True, plot_on_axis=axs[1,0], starting_agent=rerouting_agent)
    
    found_flexibility_ranges = result.plot(axs[1,0], show_atf=False, show_additional_delays=True)

    # Update the graph with the results from FlexSIPP, assume we know now the actual delay of rerouting agent 
    actual_departure_time = 3

    ax = axs[1,1]
    ax.grid(alpha=0.3)
    flexibility_agent.plot_route(ax, continues=continues, title=f"Agent {flexibility_agent.id} before", show_buffer_time=show_buffer_time)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    # Update the graph with the results from FlexSIPP, assume we know now the actual delay of Agent 2
    # TODO check discrete necessary
    atf, new_route, minimum_delays = result.get_fastest_route(actual_departure_time, agents, discrete=False)
    print(f"Best route when earliest departure time is {actual_departure_time} is with atf {atf} and route {new_route}, delaying agent {flexibility_agent} at {[f'{n} ({x:.2f})' for n, x in minimum_delays[flexibility_agent].items() if isinstance(n, Node)]}")

    ax = axs[0,1]
    ax.grid(alpha=0.3)
    temp_agent = MapfAgent(0, [node for node, interval in graph._complete_new_route(new_route)], graph.global_end_time)
    temp_agent.plot_route(ax, continues=continues, title="Original unsafe interval on found path", show_buffer_time=show_buffer_time)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    del minimum_delays[rerouting_agent]
    print(f"Updating intervals for agent {rerouting_agent} at starting at time {actual_departure_time} {new_route} with minimum delays {minimum_delays}")
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
    flexibility_agent.plot_route(ax, continues=continues, title=f"Agent {flexibility_agent.id} after", show_buffer_time=True)
    ax.set_ylim(0, graph.global_end_time)
    ax.set_yticks(range(0, graph.global_end_time + 1, 2))

    print(f"@MAEdeR Search time (python)", result_maeder)
    result_maeder.plot(axs[0,3], linestyle=3)
    
    graph.filter_out_agent(flexibility_agent)
    flexSIPP2 = FSIPP(graph, heuristic, agents, use_flexibility=True)
    flexSIPP2._write(open(os.path.join(os.path.dirname(__file__), "output", "warehouse_delay_graph_FlexSIPP_agent2.txt"), "w"))
    result2 = flexSIPP2.run_search(flexibility_agent.origin.name, flexibility_agent.destination.name, start_time, graph.global_end_time, optimize_total_delay=False, redirect_stderr="stderr_warehouse_FlexSIPP_agent2.txt")
    print(f"FlexSIPP Agent 2 Search time (python) {result2.metadata['Search Time Python']:.2f}, (c++) {result2.metadata['Search Time']} yields: ", result2)
    atf, new_route, minimum_delays = result2.get_fastest_route(2, agents, discrete=False)
    print("Found route", new_route, atf, minimum_delays)


    plt.show()
    plt.close()


if __name__ == "__main__":
    location = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", "example_warehouse", "warehouse_delay.map")
    paths = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", "example_warehouse", "paths_delay.txt")
    run_flexsipp_scenario(location, paths)
