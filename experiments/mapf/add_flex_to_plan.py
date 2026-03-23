import os
import time
import json
import math
import datetime
import random
import numpy as np
from pathlib import Path

from matplotlib import pyplot as plt

from graph import GridCell
from flexsipp.graphs.fsipp import FSIPP
from read_experiment import create_mapf_instance_from_paths

import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

if __name__ == "__main__":
    # This is the number of time steps after the start time that can be searched. 
    filename = os.path.join(os.path.dirname(__file__), "experiment_configurations_movingAI.json")
    configurations = json.load(open(filename, "r"))
    random_seed = 42
    random.seed(random_seed)
    results_flexsipp = {}
    results_maeder = {}
    date = datetime.datetime.now().strftime("%Y-%m-%d")

    config_name = "maze1"
    config_name = "warehouse1"

    location = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, configurations[config_name]["location"])
    for scenario in os.listdir(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, configurations[config_name]["scenarios"])):
        scenario_names = scenario.split("_")[0].split("-")
        agent_nums = ["k50", "k100", "k200"]
        scenario_nums = [str(x) for x in range(1, 11)]
        if ".txt" in scenario and scenario_names[7] in scenario_nums and scenario_names[8] in agent_nums:
            scenario_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, configurations[config_name]["scenarios"], scenario)
            print(scenario)
            gaps = [3, 8]

            for min_gap in gaps:
                new_scenario_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mapf", config_name, "generated", scenario.replace("_paths", f"_paths_{min_gap}"))
                stats = new_scenario_file.replace(".txt", f".json")
                with open(scenario_file, "r") as f:
                    paths = [line.split(": ")[1].strip().split("->") for line in f.readlines()]
                    stat_results = {x: [] for x in range(len(paths))}
                    for agent in range(len(paths)):
                        for other_agent in range(agent+1, len(paths)):
                            i = 0
                            while i < len(paths[agent])-1:
                                loc = paths[agent][i]
                                j = 0
                                while j < len(paths[other_agent])-1:
                                    if loc == paths[other_agent][j]:
                                        if j < i and i-j < min_gap:
                                            delay_loc = paths[agent][i-1]
                                            stat_results[agent].append((delay_loc, min_gap-(i-j)))
                                            for k in range(min_gap-(i-j)):
                                                paths[agent].insert(i+k, delay_loc)
                                            i += min_gap-(i-j)
                                    j += 1
                                i += 1
                    with open(new_scenario_file, "w") as new_file:
                        for agent, path in enumerate(paths):
                            new_file.write(f"Agent {agent}: {'->'.join(path)}\n")
                    json.dump(stat_results, open(stats, "w"), indent=4)



