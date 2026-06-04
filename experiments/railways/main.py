import argparse

from flexsipp_railways.train_agents.train_agent_limited_flexibility import \
    train_agent_limited_flexibility_generator
from flexsipp_railways.generate import graph_from_file, scenario_from_file
from flexsipp.graphs.fsipp import FSIPP

parser = argparse.ArgumentParser(
                    prog='FlexSIPP',
                    description='Given a location (file) and a scenario (file), run the FlexSIPP program')
parser.add_argument('-l', "--location-file", help = "Path to the location file", required = True)
parser.add_argument('-s', "--scenario-file", help = "Path to the scenario file", required = True)
parser.add_argument('-a', "--delay-agent", help="Identifier (int) of the agent in the scenario_file that is delayed. If not specified, the first agent in the scenario wil be chosen.", required=False, default=None)
parser.add_argument('-e', "--end-time", help="End time of the scenario, if None is given", required=False, default=None)

def run_flexsipp(location_file, scenario_file, delay_agent, scenario_end):
    railway_graph = graph_from_file(location_file)
    scenario = scenario_from_file(scenario_file, railway_graph)
    scenario.process()
    if delay_agent is None:
        delay_agent = scenario.agents['1']
    else:
        delay_agent = scenario.get_replanning_agent(int(delay_agent))
    graph = scenario.fsipp(delay_agent)
    heuristic = graph.calculate_heuristic(delay_agent.destination)
    # Currently takes in complete graph, not filtered to the agents original route
    flexSIPP = FSIPP(graph, heuristic, scenario.agents)
    result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, delay_agent.measures.start_time, redirect_stderr="stderr.txt")
    print(result)

if __name__ == "__main__":
    args = parser.parse_args()
    run_flexsipp(args.location_file, args.scenario_file, args.delay_agent, args.end_time)
