import os
import time
import json
import datetime
from matplotlib import pyplot as plt

from graph import GridCell
from flexsipp.graphs.fsipp import FSIPP
from read_experiment import create_mapf_instance_from_paths

import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

def run_flexsipp(location_file, scenario_file, delay_agent_id, max_delay=1000, scenario_end=None):
    agent_start_time = 0
    # Set up @SIPP graph without flexibility
    gen_time_maeder_start = time.time()
    maeder_graph, maeder_agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    maeder_delay_agent = maeder_agents[delay_agent_id]
    maeder_original_arrival_time = maeder_delay_agent.destination.unsafe_intervals[-1].start
    maeder_graph.filter_out_agent(maeder_delay_agent)
    maeder_heuristic = maeder_graph.calculate_heuristic(maeder_delay_agent.destination)
    maeder = FSIPP(maeder_graph, maeder_heuristic, maeder_agents, use_flexibility=False)
    gen_time_maeder_end = time.time()
    # Run @MAEDeR as a baseline
    maeder_result = maeder.run_search(maeder_delay_agent.origin.name, maeder_delay_agent.destination.name, agent_start_time, max_delay)
    maeder_result.metadata.update({
        "gen_time": gen_time_maeder_end - gen_time_maeder_start, 
        f"original_arrival_time_{delay_agent_id}": maeder_original_arrival_time,
        "unique_routes_safe":  {path: [str(a) for a in atfs] for path, atfs in maeder_result.unique_routes_eatfs.items()}
    })

    print(f"Search for path agent {delay_agent_id} from {maeder_delay_agent.origin.name} to {maeder_delay_agent.destination.name} starting between {agent_start_time} and {agent_start_time+max_delay}")
    # Set up @SIPP graph with Flexibility
    gen_time_flexsipp_start = time.time()
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    delay_agent = agents[delay_agent_id]
    original_arrival_time = delay_agent.destination.unsafe_intervals[-1].start
    graph.filter_out_agent(delay_agent)
    heuristic = graph.calculate_heuristic(delay_agent.destination)
    flexSIPP = FSIPP(graph, heuristic, agents, use_flexibility=True)
    gen_time_flexsipp_end = time.time()
    # Run FlexSIPP
    result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, agent_start_time, max_delay)
    result.metadata.update({
        "gen_time": gen_time_flexsipp_end - gen_time_flexsipp_start,
        "tipping_points": [(w, str(x), str(y), {a.id: {n.name: m for (n,m) in v.items() if isinstance(n, GridCell)} for (a,v) in z.items()}) for (w,x,y,z) in result.find_tipping_points(agents, original_arrival_time=original_arrival_time, optimize_total_delay=True, print_tipping_points=False, print_agent_delays=False)],
        "unique_routes_safe":  {path: [str(a) for a in atfs] for path, atfs in result.unique_routes_eatfs.items()}
    })
    
    data = {
        "@MAEDeR": maeder_result.metadata,
        "FlexSIPP": result.metadata,
        "search_interval": agent_start_time, 
        "max_delay": max_delay,
    }
    return data

if __name__ == "__main__":
    # This is the number of time steps after the start time that can be searched. 
    timeout = 1000
    config_name = "warehouse1"
    filename = os.path.join(os.path.dirname(__file__), "experiment_configurations_movingAI.json")
    configurations = json.load(open(filename, "r"))
    config = configurations[config_name]
    location = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, config["location"])
    for scenario in config["files"]:
        scenario_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, config["scenarios"], f"{scenario}.txt")
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        k = int(scenario.split("-")[-1].split("_")[0].replace("k", ""))
        result_dir = os.path.join(os.path.dirname(__file__), "output", config_name)
        result_file = os.path.join(result_dir, f"{scenario}_{date}_k{k}.json")
        if not os.path.isdir(result_dir):
            os.mkdir(result_dir)
        results = {f"delay_agent{agent}": {} for agent in range(1, k)}
        max_delays = 1000
        for agent in range(1, k):
            print(f"Run FlexSIPP for {scenario} with delay agent {agent}")
            results[f"delay_agent{agent}"] = run_flexsipp(location, scenario_file, agent)
            json.dump(results, open(result_file, "w"), indent=4)
