import os
import time
import json
import datetime
import random

from flexsipp_mapf.graph import GridCell
from flexsipp.graphs.fsipp import FSIPP
from read_experiment import create_mapf_instance_from_paths

import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

def run_flexsipp(location_file, scenario_file, delay_agent_id, seed, max_delay=1000, scenario_end=None, cpp_error=None):
    random.seed(seed)

    # Set up @SIPP graph without flexibility
    # gen_time_maeder_start = time.time()
    # maeder_graph, maeder_agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    # maeder_delay_agent = maeder_agents[delay_agent_id]
    # original_departure_time = maeder_delay_agent.origin.unsafe_intervals[0].end
    # original_arrival_time = maeder_delay_agent.destination.unsafe_intervals[-1].start
    # maeder_graph.filter_out_agent(maeder_delay_agent)
    # maeder_heuristic = maeder_graph.calculate_heuristic(maeder_delay_agent.destination)
    # maeder = FSIPP(maeder_graph, maeder_heuristic, maeder_agents, use_flexibility=False)
    # gen_time_maeder_end = time.time()
    # # Run @MAEDeR as a baseline
    # maeder_result = maeder.run_search(maeder_delay_agent.origin.name, maeder_delay_agent.destination.name, delayed_start_time, max_delay)
    # maeder_result.metadata.update({
    #     "gen_time": gen_time_maeder_end - gen_time_maeder_start,
    #     "unique_routes_safe":  {path: [str(a) for a in atfs] for path, atfs in maeder_result.unique_routes_eatfs.items()}
    # })

    # Set up @SIPP graph with Flexibility
    gen_time_flexsipp_start = time.time()
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    delay_agent = agents[delay_agent_id]
    original_departure_time = delay_agent.origin.unsafe_intervals[0].end
    original_arrival_time = delay_agent.destination.unsafe_intervals[-1].start
    delayed_start_time_upper_bound = original_departure_time
    if len(delay_agent.origin.unsafe_intervals) > 1:
        # Delay can be at most the time that the origin becomes unsafe again
        delayed_start_time_upper_bound = delay_agent.origin.unsafe_intervals[1].start 
    else:
        # If it remains safe, then use half the time it takes to the cross its path
        delayed_start_time_upper_bound = original_departure_time + (original_arrival_time - original_departure_time) / 2
    delayed_start_time = random.uniform(original_departure_time, delayed_start_time_upper_bound)
    print(f"Search for path agent {delay_agent_id} from {delay_agent.origin.name} to {delay_agent.destination.name} originally departing at {original_departure_time} and starting search between {delayed_start_time} and {delayed_start_time+max_delay}")
    graph.filter_out_agent(delay_agent)
    heuristic = graph.calculate_heuristic(delay_agent.destination)
    flexSIPP = FSIPP(graph, heuristic, agents, use_flexibility=True)
    gen_time_flexsipp_end = time.time()
    # Run FlexSIPP
    meta_data = {}
    try:
        result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, delayed_start_time, max_delay, redirect_stderr=f"{cpp_error}_agent-{delay_agent_id}.txt")
        result.metadata.update({
            "gen_time": gen_time_flexsipp_end - gen_time_flexsipp_start,
            "tipping_points": [(w, str(x), '->'.join([f"({n[0].name}, {n[1]})" for n in y if isinstance(n[0], GridCell)]), {a.id: {n.name: m for (n,m) in v.items() if isinstance(n, GridCell)} for (a,v) in z.items()}) for (w,x,y,z) in result.find_tipping_points(agents, original_arrival_time=original_arrival_time, optimize_total_delay=True, print_tipping_points=False, print_agent_delays=False)],
            "unique_routes_safe":  {path: [str(a) for a in atfs] for path, atfs in result.unique_routes_eatfs.items()}
        })
        meta_data = result.metadata
    except RuntimeError:
        print(f"Could not find safe starting state at {delay_agent.origin.name} at time {delayed_start_time} for agent {delay_agent_id}")
        meta_data = {
            "gen_time": gen_time_flexsipp_end - gen_time_flexsipp_start,
            "tipping_points": [],
            "unique_routes_safe": {}
        }
    
    data = {
        # "@MAEDeR": maeder_result.metadata,
        "FlexSIPP": meta_data,
        "original_departure_time": original_departure_time,
        "original_arrival_time": original_arrival_time,
        "delay_search_start_time": delayed_start_time,
        "max_delay": max_delay
    }
    return data

if __name__ == "__main__":
    random_seed = 42
    filename = os.path.join(os.path.dirname(__file__), "experiment_configurations_movingAI.json")
    configurations = json.load(open(filename, "r"))
    for config_name, config in configurations.items():
        location = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, config["location"])
        for scenario in config["files"]:
            scenario_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, config["scenarios"], f"{scenario}.txt")
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            k = int(scenario.split("-")[-1].split("_")[0].replace("k", ""))
            result_dir = os.path.join(os.path.dirname(__file__), "output", config_name)
            result_file = os.path.join(result_dir, f"tippingpoints_{scenario}_{date}_seed{random_seed}.json")
            cpp_eror_file = os.path.join(result_dir, "cpp_error", f"{scenario}_{date}_seed{random_seed}")
            if not os.path.isdir(result_dir):
                os.mkdir(result_dir)
            if not os.path.isdir(os.path.join(result_dir, "cpp_error")):
                os.mkdir(os.path.join(result_dir, "cpp_error"))
            results = {f"delay_agent{agent}": {} for agent in range(1, k+1)}
            max_delays = 1000
            for agent in range(1, k+1):
                print(f"Run FlexSIPP for {scenario} with delay agent {agent}")
                results[f"delay_agent{agent}"] = run_flexsipp(location, scenario_file, agent, random_seed, cpp_error=cpp_eror_file)
                json.dump(results, open(result_file, "w"), indent=4)
