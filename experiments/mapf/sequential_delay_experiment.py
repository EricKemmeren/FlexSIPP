import os
import time
import json
import math
import datetime
import random
from matplotlib import pyplot as plt

from graph import GridCell
from flexsipp.graphs.fsipp import FSIPP
from read_experiment import create_mapf_instance_from_paths

import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)


def repeated_delays(location_file, scenario_file, num_delays, scenario_end=None):
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    epsilon = 0.001
    complete_result = {f"delay{i}": {} for i in range(num_delays)}
    delays = []
    for idx in range(num_delays):
        a = random.choice(list(agents.keys()))
        t = random.uniform(0, agents[a].destination.unsafe_intervals[-1].start-1)
        delays.append((t, a))
    # Sort delays by time
    delays.sort(key=lambda x: x[0])

    for delay_idx, (delay_at_time, delay_agent_id) in enumerate(delays):
        gen_time_start = time.time()
        delay_agent = agents[delay_agent_id]
        original_arrival_time = delay_agent.destination.unsafe_intervals[-1].start
        delay_origin = delay_agent.get_location_at_time(delay_at_time)
        print(f"Now delaying agent {delay_agent_id} at time {delay_at_time} at node {delay_origin}")

        # Filter out that agents unsafe intervals
        graph.filter_out_agent(delay_agent)

        # Pre calculate the heuristic
        heuristic = graph.calculate_heuristic(delay_agent.destination)

        # Create safe intervals and calculate the ATFs
        flexSIPP = FSIPP(graph, heuristic, agents)
        gen_time_end = time.time()

        # Run the expansion A* search
        result = flexSIPP.run_search(delay_origin, delay_agent.destination, delay_at_time, max_delay=delay_at_time+epsilon)

        post_time_start = time.time()
        # Pick a route from the results the agent will take, currently selecting a given amount of delay
        atf, new_route, minimum_delays = result.get_fastest_route(delay_at_time, agents, discrete=True)    
        # Update the unsafe intervals such that it can be used again
        del minimum_delays[delay_agent]
        graph.update_unsafe_intervals(new_path=(delay_agent, new_route, delay_at_time), minimum_delays=minimum_delays)
        for agent, flexibility_used in minimum_delays.items():
            agent.update_wait_time_with_flexibility(flexibility_used)
        post_time_end = time.time()
        
        result.metadata.update({
            "delay_agent": delay_agent.id,
            "delay_at_time": delay_at_time,
            "original_arrival_time": original_arrival_time,
            "epsilon": epsilon,
            "preprocess_time": gen_time_end - gen_time_start,
            "postprocess_time": post_time_end - post_time_start,
            "unique_routes_safe":  {path: [str(a) for a in atfs] for path, atfs in result.unique_routes_eatfs.items()}
        })
        complete_result[f"delay{delay_idx}"] = result.metadata
    return complete_result


if __name__ == "__main__":
    # This is the number of time steps after the start time that can be searched. 
    timeout = 1000
    random.seed(123)
    config_name = "warehouse1"
    filename = os.path.join(os.path.dirname(__file__), "experiment_configurations_movingAI.json")
    configurations = json.load(open(filename, "r"))
    config = configurations[config_name]
    location = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, config["location"])
    results = {s: {} for s in config["files"]}
    for scenario in config["files"]:
        scenario_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, config["scenarios"], f"{scenario}.txt")
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        k = int(scenario.split("-")[-1].split("_")[0].replace("k", ""))
        num_delays = int(math.floor(k / 3))
        print("Run scenario", scenario, "with", num_delays, "delays")
        result_dir = os.path.join(os.path.dirname(__file__), "output", config_name)
        result_file = os.path.join(result_dir, f"replan_{scenario}_{date}_d{num_delays}.json")
        if not os.path.isdir(result_dir):
            os.mkdir(result_dir)
        results[scenario] = repeated_delays(location, scenario_file, num_delays)
        json.dump(results, open(result_file, "w"), indent=4)
