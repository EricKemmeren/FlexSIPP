import argparse

from flexsipp.graphs.fsipp import FSIPP
from read_experiment import create_mapf_instance_from_paths

parser = argparse.ArgumentParser(
                    prog='FlexSIPP',
                    description='Given a location (file) and a scenario (file), run the FlexSIPP program')
parser.add_argument('-l', "--location-file", help = "Path to the location file", required = True)
parser.add_argument('-s', "--scenario-file", help = "Path to the scenario file", required = True)
parser.add_argument('-a', "--delay-agent", help="Identifier (int) of the agent in the scenario_file that is delayed. If not specified, the first agent in the scenario wil be chosen.", required=False, default=None)
parser.add_argument('-e', "--end-time", help="End time of the scenario, if None is given", required=False, default=None)

def run_flexsipp(location_file, scenario_file, delay_agent, scenario_end):
    # TODO the merging of intervals is not from the same agent, so we get an assertion error
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    if delay_agent is None:
        delay_agent = agents[0]
    else:
        delay_agent = agents[int(delay_agent)]
    heuristic = {node.name: 0 for node in graph.nodes.values()}
    flexSIPP = FSIPP(graph, heuristic, len(agents))
    result = flexSIPP.run_search(1000, delay_agent.origin.name, delay_agent.destination.name, delay_agent.measures.start_time)
    # TODO readable output
    print(result)

if __name__ == "__main__":
    args = parser.parse_args()
    run_flexsipp(args.location_file, args.scenario_file, args.delay_agent, args.end_time)
