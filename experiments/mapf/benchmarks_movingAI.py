import os
import time
import json
from matplotlib import pyplot as plt

from flexsipp.graphs.fsipp import FSIPP
from read_experiment import create_mapf_instance_from_paths

import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

def run_flexsipp(location_file, scenario_file, delay_agent_id, max_delay=1000, scenario_end=None):
    gen_time_start = time.time()
    maeder_graph, maeder_agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    assert delay_agent_id in agents, f"ERROR: no delay agent with id {delay_agent_id} in the set of agents."
    delay_agent = agents[delay_agent_id]
    graph.filter_out_agent(delay_agent)
    maeder_delay_agent = maeder_agents[delay_agent_id]
    maeder_graph.filter_out_agent(maeder_delay_agent)
    heuristic = graph.calculate_heuristic(delay_agent.destination)
    maeder = FSIPP(maeder_graph, heuristic, maeder_agents, use_flexibility=False)
    flexSIPP = FSIPP(graph, heuristic, agents, use_flexibility=True)
    gen_time_end = time.time()

    start_time = 0
    print(f"Search for path agent {delay_agent_id} from {delay_agent.origin.name} to {delay_agent.destination.name} starting between {start_time} and {start_time+max_delay}")
    # Run @MAEDeR as a baseline
    maeder_result = maeder.run_search(delay_agent.origin.name, delay_agent.destination.name, start_time, max_delay)
    maeder_result.metadata.update({"unique_routes_safe":  {path: [str(a) for a in atfs] for path, atfs in maeder_result.unique_routes_eatfs.items()}})
    # Run FlexSIPP
    result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, start_time, max_delay)
    result.metadata.update({"unique_routes_safe":  {path: [str(a) for a in atfs] for path, atfs in result.unique_routes_eatfs.items()}, "tipping_points": result.find_tipping_points()})
    
    data = {
        "@MAEDeR": maeder_result.metadata,
        "FlexSIPP": result.metadata,
        "search_interval": start_time, 
        "max_delay": max_delay,
        "generation_time": gen_time_end - gen_time_start
    }
    print(f"Generation took {data['generation_time']} and FlexSIPP search took {result.metadata["Search Time"]}")
    return data

if __name__ == "__main__":
    # This is the number of time steps after the start time that can be searched. 
    timeout = 1000
    config_name = "maze1"
    filename = os.path.join(os.path.dirname(__file__), "experiment_configurations_movingAI.json")
    configurations = json.load(open(filename, "r"))
    config = configurations[config_name]
    location = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, config["location"])
    for scenario in config["files"]:
        scenario_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, config["scenarios"], f"{scenario}.txt")
        k = int(scenario.split("-")[-1].split("_")[0].replace("k", ""))
        k = 5
        config["results"][scenario] = {}
        max_delays = 1000
        for agent in range(1, k):
            print(f"Run FlexSIPP for {scenario} with delay agent {agent}")
            res = run_flexsipp(location, scenario_file, agent)
            config["results"][scenario][agent] = res
        json.dump(configurations, open(filename, "w"), indent=4)
