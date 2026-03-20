import os
import time
import json
import math
import datetime
import random
from pathlib import Path
import numpy as np

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
    random_gen = np.random.default_rng(seed)
    chosen_agents = random_gen.permutation(np.array(list(agents.values())))
    for idx in range(num_delays):
        # Get a random agent
        a = chosen_agents[idx]
        # Get a random node on this agent's path
        loc: GridCell = random.choice([node for node in a.route if isinstance(node, GridCell)])
        ui_a_end = max([ui for ui in loc.unsafe_intervals if ui.by_agent == a])
        # Get the first unsafe interval at the delay location after the delayed agent visits
        index = loc.unsafe_intervals.bisect_right(ui_a_end)
        safe_end = loc.unsafe_intervals[index].start if index < len(loc.unsafe_intervals) else graph.global_end_time
        delayed_start_time = random.uniform(max(0, ui_a_end.start), max(0, safe_end))
        delays.append((a.id, loc, delayed_start_time, ui_a_end.start))
    # Sort delays by time
    delays.sort(key=lambda x: x[2])
    return delays


def repeated_delays(location_file, scenario_file, delays, result_file, scenario_end=None, use_flexibility=True):
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    epsilon = 0.001
    complete_result = {f"delay{i}": {} for i in range(len(delays))}
    initial_paths = {
        id: {
            "departure": (agent.origin.name, agent.origin.unsafe_intervals[0].end),
            "arrival": (agent.destination.name, agent.destination.unsafe_intervals[-1].start)
        } for id, agent in agents.items()}
    for delay_idx, (delay_agent_id, delay_origin, delayed_start_time, original_start_time) in enumerate(delays):
        delay_agent = agents[delay_agent_id]
        gen_time_start = time.time()
        original_arrival_time = delay_agent.destination.unsafe_intervals[-1].start
        print(f"Now {delay_idx} delaying agent {delay_agent} at time {delayed_start_time} at node {delay_origin} with original start time {original_start_time}  using flexibility: {use_flexibility}")

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
            result = flexSIPP.run_search(delay_origin, delay_agent.destination, delayed_start_time, max_delay=delayed_start_time+epsilon, optimize_total_delay=True, redirect_stderr="stderr.txt")
        except RuntimeError:
            print(f"Could not find safe starting state at {delay_origin} at time {delayed_start_time} for agent {delay_agent}")
            failure = True

        meta_data = {}
        post_time_start = time.time()
        if not failure:
            # Pick a route from the results the agent will take, currently selecting a given amount of delay
            atf, new_route, minimum_delays = result.get_fastest_route(delayed_start_time, agents, discrete=True, print_agent_delays=False)
            result.metadata.update({
                "unique_routes_safe":  {path: [str(a) for a in atfs] for path, atfs in result.unique_routes_eatfs.items()},
                "path_differences": result.compare_paths([str(node) for node in delay_agent.route if isinstance(node, GridCell)])
            })
            meta_data = result.metadata

        # Update the unsafe intervals such that it can be used again
        if failure or not new_route:
            print(f"Could not find a route for agent {delay_agent} starting at time {delayed_start_time}")
            graph.update_unsafe_intervals(new_path=(delay_agent, [(delay_agent.destination, (0, graph.global_end_time))], delayed_start_time), minimum_delays={})
        else:
            del minimum_delays[delay_agent]
            graph.update_unsafe_intervals(new_path=(delay_agent, new_route, delayed_start_time), minimum_delays=minimum_delays)
            for agent, flexibility_used in minimum_delays.items():
                agent.update_wait_time_with_flexibility(flexibility_used)
            meta_data.update({
                "delays": {a.id: {n.name: m for (n,m) in v.items() if isinstance(n, GridCell)} for (a,v) in minimum_delays.items()}
            })
        post_time_end = time.time()
        
        result.metadata.update({
            "delay_agent": delay_agent.id,
            "delayed_start_time": delayed_start_time,
            "original_start_time": original_start_time,
            "original_arrival_time": original_arrival_time,
            "epsilon": epsilon,
            "preprocess_time": gen_time_end - gen_time_start,
            "postprocess_time": post_time_end - post_time_start,
            "arrival_times": {agent_id: {
                "departure": (agent.origin.name, agent.origin.unsafe_intervals[0].end),
                "arrival": (agent.destination.name, agent.destination.unsafe_intervals[-1].start)
            } for agent_id, agent in agents.items()}
        })
        if delay_idx == 0:
            result.metadata.update({"initial_paths": initial_paths})
        complete_result[f"delay{delay_idx}"] = result.metadata
        json.dump(complete_result, open(result_file, "w"), indent=4)
    return complete_result


if __name__ == "__main__":
    # This is the number of time steps after the start time that can be searched. 
    filename = os.path.join(os.path.dirname(__file__), "experiment_configurations_movingAI.json")
    configurations = json.load(open(filename, "r"))
    random_seed = 123
    config = ("warehouse1", "warehouse-20-40-10-2-1.map", "warehouse-20-40-10-2-1-random-1-k200", "scen-random")
    config = ("maze1", "maze-128-128-1.map", "maze-128-128-1-even-1-k50", "scen-even")
    location = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config[0], config[1])
    scenario_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config[0], config[3], f"{config[2]}_paths.txt")
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    k = int(config[2].split("-")[-1].replace("k", ""))
    num_delays = int(math.floor(k / 2))
    print("Run scenario", config[2], "with", num_delays, "delays")
    result_dir = os.path.join(os.path.dirname(__file__), "output", config[0])
    result_file = os.path.join(result_dir, f"replan_{config[2]}_{date}_seed{random_seed}_{num_delays}delays.json")

    if not os.path.isdir(result_dir):
        Path(result_dir).mkdir(parents=True)
    delays = get_delays_from_seed(location, scenario_file, num_delays, random_seed)

    repeated_delays(location, scenario_file, delays, result_file, use_flexibility=True)
