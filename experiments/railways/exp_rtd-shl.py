import logging
import os
import sys
from pathlib import Path
from matplotlib import pyplot as plt

from flexsipp_railways.generate import graph_from_file, scenario_from_file
from flexsipp.graphs.fsipp import FSIPP

# Disable logging of the program in the notebook
os.environ["LOGLEVEL"] = "CRITICAL"

# Use an argument to select the scenario file
scen_num = int(sys.argv[1]) - 1

logging.basicConfig()
logging.root.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('__main__')
logger.setLevel(os.environ.get("LOGLEVEL", logging.FATAL))

pybooklogger = logging.getLogger('pybook')
pybooklogger.setLevel(logging.DEBUG)

### Load the graphs
layout_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "railways", "prorail", "netherlands-schiphol.json")
layout = graph_from_file(layout_file)

### Load the scenarios
basepath = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "railways", "case_study_scenarios"))
scenario_files = ["2025-07-08_1.json", "2025-07-08_2.json", "2025-07-08_3.json", "2025-07-08_4.json"]
print("Using scenario file", scenario_files[scen_num])
tad_exp = scenario_from_file(basepath / scenario_files[scen_num], layout)
tad_exp.process()
delay_agent = tad_exp.get_replanning_agent("1867")

### Run the experiment
graph = tad_exp.fsipp(delay_agent)
heuristic = graph.calculate_heuristic(delay_agent.destination)
allowed_dpt = {"Rtd", "Rmoa_Rtd", "Sdm", "Dt_Sdm", "Dtcp", "Dt", "Dt_Gv", "Gvmw", "Gv", "Laa", "Gvm", "Gvm_Ledn", "Ledn", "Hfd_Ledn", "Hfd", "Hfd_Shl", "Shl"}
print("Constructed FSIPP graph and calculated heuristic")

filter_nodes = {node for name, node in graph.nodes.items() if name.split("|")[0] in allowed_dpt}
flexSIPP = FSIPP(graph, heuristic, tad_exp.agents, filter_nodes=filter_nodes)
result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, delay_agent.measures.start_time, optimize_total_delay=False, find_first_path=False, redirect_stderr="stderr_Eurostar.txt", redirect_stdout="stdout_Eurostar.txt", write_fsipp_graph="fsipp_Eurostar_graph.txt", store_fsipp_output="fsipp_Eurostar_search.json")

### Show the results
fig, axs = plt.subplots(2, 1, figsize=(5, 10), sharex=True)
result.plot(axs[0], linestyle=3)
result.plot(axs[1], show_atf=False, show_total_delays=True, original_arrival_time=delay_agent.measures.start_time)
fig.savefig("fsipp_eurostar.png")

tipping_points = result.find_tipping_points(delay_agent, delay_agent.measures.start_time, tad_exp.agents, optimize_total_delay=False, print_tipping_points=True, print_agent_delays=True)
with open("tipping_points_eurostar.txt", "w") as f:
    f.write(tipping_points)
