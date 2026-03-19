import os
import time
import json
import math
import datetime
import random
from pathlib import Path

from graph import GridCell
from flexsipp.graphs.fsipp import FSIPP
from read_experiment import create_mapf_instance_from_paths

import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

def get_delays_from_seed(location_file, scenario_file, num_delays, seed=123, scenario_end=None):
    random.seed(seed)
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    delays = []
    for idx in range(num_delays):
        # Get a random agent
        a = random.choice(list(agents.values()))
        # Get a random node on this agent's path
        loc: GridCell = random.choice([node for node in a.route if isinstance(node, GridCell)])
        ui_a_end = max([ui for ui in loc.unsafe_intervals if ui.by_agent == a])
        index = loc.unsafe_intervals.bisect_right(ui_a_end)
        safe_end = loc.unsafe_intervals[index].start - 10 if index < len(loc.unsafe_intervals) else 100
        delay = random.uniform(max(0, min(10, safe_end)), min(100, safe_end))
        delays.append((a.id, loc, delay))
    # Sort delays by time
    delays.sort(key=lambda x: x[2])
    return delays


def repeated_delays(location_file, scenario_file, delays, scenario_end=None, use_flexibility=True):
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    epsilon = 0.001
    complete_result = {f"delay{i}": {} for i in range(len(delays))}
    initial_paths = {
        id: {
            "departure": (agent.origin.name, agent.origin.unsafe_intervals[0].end),
            "arrival": (agent.destination.name, agent.destination.unsafe_intervals[-1].start)
        } for id, agent in agents.items()}
    for delay_idx, (delay_agent_id, delay_origin, delay_at_time) in enumerate(delays):
        delay_agent = agents[delay_agent_id]
        gen_time_start = time.time()
        original_arrival_time = delay_agent.destination.unsafe_intervals[-1].start
        print(f"Now {delay_idx} delaying agent {delay_agent} at time {delay_at_time} at node {delay_origin} using flexibility: {use_flexibility}")

        # Filter out that agents unsafe intervals
        graph.filter_out_agent(delay_agent)

        # Pre calculate the heuristic
        heuristic = graph.calculate_heuristic(delay_agent.destination)

        # Create safe intervals and calculate the ATFs
        flexSIPP = FSIPP(graph, heuristic, agents, use_flexibility=use_flexibility)
        gen_time_end = time.time()

        failure = False
        # Run the expansion A* search
        try:
            result = flexSIPP.run_search(delay_origin, delay_agent.destination, delay_at_time, max_delay=delay_at_time+epsilon, optimize_total_delay=True, redirect_stderr="stderr.txt")
        except RuntimeError:
            print(f"Could not find safe starting state at {delay_origin} at time {delay_at_time} for agent {delay_agent}")
            failure = True

        post_time_start = time.time()
        if not failure:
            # Pick a route from the results the agent will take, currently selecting a given amount of delay
            atf, new_route, minimum_delays = result.get_fastest_route(delay_at_time, agents, discrete=True, print_agent_delays=False)

        if not failure:
            path_differences = result.compare_paths([str(node) for node in delay_agent.route if isinstance(node, GridCell)])
        else:
            path_differences = "{}"

        # Update the unsafe intervals such that it can be used again
        if failure or not new_route:
            print(f"Could not find a route for agent {delay_agent} starting at time {delay_at_time}")
            graph.update_unsafe_intervals(new_path=(delay_agent, [(delay_agent.destination, (0, graph.global_end_time))], delay_at_time), minimum_delays={})
        else:
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
            "tipping_points": [(w, str(x), '->'.join([f"({n.name}, {m})" for (n,m) in y]), {a.id: {n.name: m for (n,m) in v.items() if isinstance(n, GridCell)} for (a,v) in z.items()}) for (w,x,y,z) in result.find_tipping_points(agents, original_arrival_time=original_arrival_time, optimize_total_delay=True, print_tipping_points=False, print_agent_delays=False)],
            "unique_routes_safe":  {path: [str(a) for a in atfs] for path, atfs in result.unique_routes_eatfs.items()},
            "path_differences": path_differences,
        })
        complete_result[f"delay{delay_idx}"] = result.metadata
    complete_result[f"delay0"]["initial_paths"] = initial_paths
    complete_result[f"delay{delay_idx}"]["final_paths"] = {
        id: {
            "departure": (agent.origin.name, agent.origin.unsafe_intervals[0].end),
            "arrival": (agent.destination.name, agent.destination.unsafe_intervals[-1].start)
        } for id, agent in agents.items()}
    return complete_result


if __name__ == "__main__":
    # This is the number of time steps after the start time that can be searched. 
    filename = os.path.join(os.path.dirname(__file__), "experiment_configurations_movingAI.json")
    configurations = json.load(open(filename, "r"))
    random_seed = 123
    for config_name, config in configurations.items():
        location = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, config["location"])
        results_flexsipp = {s: {} for s in config["files"]}
        results_maeder = {s: {} for s in config["files"]}
        for scenario in config["files"]:
            scenario_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, config["scenarios"], f"{scenario}.txt")
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            k = int(scenario.split("-")[-1].split("_")[0].replace("k", ""))
            num_delays = 1
            print("Run scenario", scenario, "with", num_delays, "delays")
            result_dir = os.path.join(os.path.dirname(__file__), "output", config_name)
            result_file = os.path.join(result_dir, f"replan_maeder_{scenario}_{date}_seed{random_seed}_{num_delays}delays.json")

            if not os.path.isdir(result_dir):
                Path(result_dir).mkdir(parents=True)
            delays = get_delays_from_seed(location, scenario_file, num_delays, random_seed)

            result_file_flexsipp = os.path.join(result_dir, f"replan_FlexSIPP_{config_name}_{date}_seed{random_seed}.json")
            results_flexsipp[scenario] = repeated_delays(location, scenario_file, delays, use_flexibility=True)
            json.dump(results_flexsipp, open(result_file_flexsipp, "w"), indent=4)

            result_file_maeder = os.path.join(result_dir, f"replan_@MAEDeR_{config_name}_{date}_seed{random_seed}.json")
            results_maeder[scenario] = repeated_delays(location, scenario_file, delays, use_flexibility=False)
            json.dump(results_maeder, open(result_file_maeder, "w"), indent=4)
