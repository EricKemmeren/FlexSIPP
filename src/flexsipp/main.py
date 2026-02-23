import json
import argparse

from flexsipp.graphs.fsipp import FSIPP
from flexsipp.generate import graph_from_file
from flexsipp.generate import scenario_from_file
from flexsipp.railways.train_agents.train_agent_limited_flexiblity import train_agent_limited_flexibility_generator

parser = argparse.ArgumentParser(
                    prog='FlexSIPP',
                    description='Given a location (file) and a scenario (file), run the FlexSIPP program')
parser.add_argument('-l', "--location-file", help = "Path to the location file", required = True)
parser.add_argument('-s', "--scenario-file", help = "Path to the scenario file", required = True)
parser.add_argument('-a', "--delay-agent", help="Identifier (int) of the agent in the scenario_file that is delayed. If not specified, the first agent in the scenario wil be chosen.", required=False, default=None)
parser.add_argument('-t', "--type", help="Type of location/scenario, default is 'railway', but can also be set to 'mapf'", required=False, default="railway")

def run_flexsipp(location_file, scenario_file, delay_agent, instance_type):
    if instance_type == "railway":
        railway_graph = graph_from_file(location_file)
        scenario = scenario_from_file(scenario_file, railway_graph)
        scenario.process()
        # TODO how to set up flexibility here?
        if delay_agent is None:
            delay_agent = scenario.agents[0]
        else:
            delay_agent = scenario.get_replanning_agent(int(delay_agent))
        heuristic = {node.name: 0 for node in railway_graph.nodes.values()}
        flexSIPP = FSIPP(scenario.fsipp(delay_agent), heuristic)
        result = flexSIPP.run_search(1000, delay_agent.origin.name, delay_agent.destination.name, delay_agent.measures.start_time)
        # TODO readable output
        print(result)
    elif instance_type == "mapf":
        # TODO scenario and location graph for non-railway specific applications
        pass
    else:
        print(f"ERROR: do not know instance type {instance_type}, please specify either 'railway' or 'mapf'")

if __name__ == "__main__":
    args = parser.parse_args()
    run_flexsipp(args.location_file, args.scenario_file, args.delay_agent, args.type)
