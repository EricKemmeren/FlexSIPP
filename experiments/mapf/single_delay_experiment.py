import os
import time
import json
import datetime
import random
from pathlib import Path

from flexsipp_mapf.graph import GridCell
from flexsipp.graphs.fsipp import FSIPP
from read_experiment import create_mapf_instance_from_paths

import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

def get_delays_from_seed(location_file, scenario_file, num_delays, scenario_end=None):
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    delays = []
    agent_list = list(agents.values())
    random.shuffle(agent_list)
    for idx in range(num_delays):
        # Get a random agent
        a = agent_list[idx]
        # Get a random node on this agent's path
        available_route = a.route[:len(a.route)//4] if len(a.route) > 10 else a.route
        loc: GridCell = random.choice([node for node in available_route if isinstance(node, GridCell)])
        ui_a_end = max([ui for ui in loc.unsafe_intervals if ui.by_agent == a])
        # Get the first unsafe interval at the delay location after the delayed agent visits
        index = loc.unsafe_intervals.bisect_right(ui_a_end)
        safe_end = loc.unsafe_intervals[index].start if index < len(loc.unsafe_intervals) else graph.global_end_time
        delayed_start_time = random.uniform(max(0, ui_a_end.start), max(0, safe_end))
        delays.append((a.id, loc, delayed_start_time, ui_a_end.start))
    # Sort delays by time
    delays.sort(key=lambda x: x[2])
    return delays



def single_delay(location_file, scenario_file, delays, scenario_end=None, use_flexibility=True):
    graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end)
    epsilon = 0.001
    initial_paths = {
        id: {
            "departure": (agent.origin.name, agent.origin.unsafe_intervals[0].end),
            "arrival": (agent.destination.name, agent.destination.unsafe_intervals[-1].start)
        } for id, agent in agents.items()}
    # Get the delay for this iteration
    delay_idx = 0
    delay_agent_id, delay_origin, delayed_start_time, original_start_time = delays[delay_idx]

    delay_agent = agents[delay_agent_id]
    gen_time_start = time.time()
    original_arrival_time = delay_agent.destination.unsafe_intervals[-1].start
    print(f"Now {delay_idx} delaying agent {delay_agent} at time {delayed_start_time} at node {delay_origin} with original start time {original_start_time} using flexibility: {use_flexibility}")
    
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
        atf, new_route, minimum_delays, _ = result.get_fastest_route(delayed_start_time, agents, discrete=True, print_agent_delays=False)
        result.metadata.update({
            "unique_routes_safe": {path: [str(a) for a in atfs] for path, atfs in result.unique_routes_eatfs.items()},
            "path_differences": result.compare_paths([str(node) for node in delay_agent.route if isinstance(node, GridCell)])
        })
        meta_data = result.metadata
    else:
        meta_data = {
            "unique_routes_safe": {},
            "path_differences": "",
            "delays": {}
        }

    # Update the unsafe intervals to retrieve the final paths and actual delays
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
    
    meta_data.update({
        "delay_agent": delay_agent.id,
        "delayed_start_time": delayed_start_time,
        "delay": delayed_start_time - original_start_time,
        "original_arrival_time": original_arrival_time,
        "epsilon": epsilon,
        "preprocess_time": gen_time_end - gen_time_start,
        "postprocess_time": post_time_end - post_time_start,
        "initial_paths": initial_paths,
        "final_paths": {
            id: {
                "departure": (agent.origin.name, agent.origin.unsafe_intervals[0].end),
                "arrival": (agent.destination.name, agent.destination.unsafe_intervals[-1].start)
            } for id, agent in agents.items()}
    })
    complete_result = {f"delay{delay_idx}": meta_data}
    return complete_result


if __name__ == "__main__":
    random_seed = 123
    num_delays = 1
    results_flexsipp = {}
    results_maeder = {}
    file_with_previous_runs = os.path.join(os.path.dirname(__file__), "run_single_delay_experiment.csv")
    date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")

    for config_name in ["maze1", "warehouse1"]:
        print("Running config", config_name)
        result_dir = Path(__file__).parent / "output" / config_name
        result_dir.mkdir(exist_ok=True, parents=True)
        result_file_maeder   = result_dir / f"optimal_{config_name}_@MAEDeR_{date}_seed{random_seed}.json"
        result_file_flexsipp = result_dir / f"optimal_{config_name}_FlexSIPP_{date}_seed{random_seed}.json"

        data_dir = Path(__file__).parent.parent.parent / "data" / "mapf" / config_name

        # Get location files in the current directory, these files end with .map
        locations = data_dir.glob("*.map")
        for location in locations:
            scenario_files = data_dir.rglob(f"{location.stem}*_paths*.txt")
            for scenario_file in scenario_files:
                scenario = scenario_file.stem

                if len(scenario.split("_paths")[-1]) == 0:
                    scenario = scenario + "_0"

                # Set random seed such that it is repeatable
                random.seed(random_seed)
                for x in range(3):
                    print("Run scenario", scenario, x, "with", num_delays, "delays")

                    delays = get_delays_from_seed(location, scenario_file, num_delays)

                    if f"{random_seed},{config_name},{location},{scenario_file},{x}\n" in open(file_with_previous_runs, "r").readlines():
                        continue

                    results_flexsipp.update(
                        {f"{scenario}_{x}": single_delay(location, scenario_file, delays, use_flexibility=True)})
                    with open(result_file_flexsipp, "w") as f:
                        json.dump(results_flexsipp, f, indent=4)

                    results_maeder.update(
                        {f"{scenario}_{x}": single_delay(location, scenario_file, delays, use_flexibility=False)})
                    with open(result_file_maeder, "w") as f:
                        json.dump(results_maeder, f, indent=4)

                    with open(file_with_previous_runs, "a") as f:
                        f.write(f"{random_seed},{config_name},{location},{scenario_file},{x}\n")
