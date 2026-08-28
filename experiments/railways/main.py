import argparse
from matplotlib import pyplot as plt

from flexsipp_railways.generate import graph_from_file, scenario_from_file
from flexsipp.graphs.fsipp import FSIPP
from flexsipp.graphs.graph import Node, Edge

parser = argparse.ArgumentParser(
                    prog='FlexSIPP',
                    description='Given a location (file) and a scenario (file), run the FlexSIPP program')
parser.add_argument('-l', "--location-file", help = "Path to the location file", required = True)
parser.add_argument('-s', "--scenario-file", help = "Path to the scenario file", required = True)
parser.add_argument('-a', "--delay-agent", help="Identifier (int) of the agent in the scenario_file that is delayed. If not specified, the first agent in the scenario wil be chosen.", required=False, default=None)
parser.add_argument('-e', "--end-time", help="End time of the scenario, if None is given", required=False, default=None)

def run_flexsipp(location_file, scenario_file, delay_agent, scenario_end=None):
    railway_graph = graph_from_file(location_file, scenario_end)
    scenario = scenario_from_file(scenario_file, railway_graph)
    scenario.process()
    if delay_agent is None:
        delay_agent = scenario.agents["1"]
    else:
        delay_agent = scenario.get_replanning_agent(delay_agent)
    graph = scenario.fsipp(delay_agent)
    heuristic = graph.calculate_heuristic(delay_agent.destination)
    flexSIPP = FSIPP(graph, heuristic, scenario.agents, filter_nodes=[node for node in delay_agent.route if isinstance(node, Node)], filter_edges=[edge for edge in delay_agent.route if isinstance(edge, Edge)])
    result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, delay_agent.measures.start_time, redirect_stderr="stderr.txt")
    result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, delay_agent.measures.start_time, optimize_total_delay=False, find_first_path=False, redirect_stderr="stderr_railways.txt", redirect_stdout="stdout_railways.txt", write_fsipp_graph="fsipp_graph_railways.txt", store_fsipp_output="fsipp_search_railways.json")

    ### Show the results
    fig, axs = plt.subplots(2, 1, figsize=(5, 10), sharex=True)
    result.plot(axs[0], linestyle=3)
    result.plot(axs[1], show_atf=False, show_total_delays=True, original_arrival_time=delay_agent.measures.start_time)
    fig.savefig("fsipp_railways.png")

    result.find_tipping_points(delay_agent, delay_agent.measures.start_time, scenario.agents, optimize_total_delay=False, print_tipping_points=True, print_agent_delays=True)

if __name__ == "__main__":
    args = parser.parse_args()
    run_flexsipp(args.location_file, args.scenario_file, args.delay_agent, args.end_time)
