import os
import datetime
import random
from pathlib import Path

import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

if __name__ == "__main__":
    # This is the number of time steps after the start time that can be searched. 
    flex_gaps = [3, 5, 8]

    random_seed = 42
    random.seed(random_seed)
    results_flexsipp = {}
    results_maeder = {}
    date = datetime.datetime.now().strftime("%Y-%m-%d")

    for config_name in ["maze1", "warehouse1"]:
        data_dir = Path(__file__).parent.parent.parent / "data" / "mapf" / config_name
        location = next(data_dir.glob("*.map"), None)
        if location is None:
            raise FileNotFoundError(f"No .map files in {data_dir}")

        scenario_pattern = f"scen*/{location.stem}*_paths.txt"
        for scenario in sorted([x for x in data_dir.rglob(scenario_pattern)]):
            for min_gap in flex_gaps:
                print(f"Create new file {os.path.split(scenario)[-1]} with flex {min_gap}")
                new_scenario_file = str(scenario).replace("_paths", f"_paths_{min_gap}")
                if os.path.isfile(new_scenario_file):
                    continue
                with open(scenario, "r") as f:
                    paths = [line.split(": ")[1].strip().split("->") for line in f.readlines()]
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
                                            for k in range(min_gap-(i-j)):
                                                paths[agent].insert(i+k, delay_loc)
                                            i += min_gap-(i-j)
                                    j += 1
                                i += 1
                    with open(new_scenario_file, "w") as new_file:
                        for agent, path in enumerate(paths):
                            new_file.write(f"Agent {agent}: {'->'.join(path)}\n")
