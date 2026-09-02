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
outdir = f"resultsEurostar{scen_num}"
if not os.path.isdir(outdir):
    os.mkdir(outdir)

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
print("Processed location file and constructed block graph.")

### Load the scenarios
basepath = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "railways", "case_study_scenarios"))
scenario_files = ["2025-07-08_1.json", "2025-07-08_2.json", "2025-07-08_3.json", "2025-07-08_4.json"]
print("Using scenario file", scenario_files[scen_num])
tad_exp = scenario_from_file(basepath / scenario_files[scen_num], layout)
tad_exp.process_blocking_time_intervals()
tad_exp.compute_flexibility()
delay_agent = tad_exp.get_replanning_agent("1867")
print("Computed unsafe intervals and flexibility.")

# Run the experiment with FlexSIPP
graph = tad_exp.fsipp(delay_agent)
heuristic = graph.calculate_heuristic(delay_agent.destination)
allowed_dpt = {"Rtd", "Rmoa_Rtd", "Sdm", "Dt_Sdm", "Dtcp", "Dt", "Dt_Gv", "Gvmw", "Gv", "Laa", "Gvm", "Gvm_Ledn", "Ledn", "Hfd_Ledn", "Hfd", "Hfd_Shl", "Shl"}
print("Constructed FSIPP graph and calculated heuristic")

filter_nodes = {node for name, node in graph.nodes.items() if name.split("|")[0] in allowed_dpt}
flexSIPP = FSIPP(graph, heuristic, tad_exp.agents, filter_nodes=filter_nodes)
result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, delay_agent.measures.start_time, optimize_total_delay=False, find_first_path=False, 
                             redirect_stderr=f"{outdir}/stderr_FlexSIPP_Eurostar-{scen_num}.txt", 
                             redirect_stdout=f"{outdir}/stdout_FlexSIPP_Eurostar-{scen_num}.txt", 
                             write_fsipp_graph=f"{outdir}/fsipp_FlexSIPP_Eurostar_graph-{scen_num}.txt", 
                             store_fsipp_output=f"{outdir}/fsipp_FlexSIPP_Eurostar_search-{scen_num}.json")
print("Ran the FlexSIPP algorithm")

# Compute the tipping points
tipping_points = result.find_tipping_points(delay_agent, delay_agent.measures.start_time, tad_exp.agents, optimize_total_delay=False, print_tipping_points=True, print_agent_delays=True)
with open(f"{outdir}/tipping_points_eurostar-{scen_num}.txt", "w") as f:
    for (tipping_point, tipping_location, minimum_delays) in tipping_points:
        f.write(f"{tipping_point},{tipping_location},{minimum_delays}")
print("Computed the tipping points")

# Run the experiment with @MAEDeR
maeder = FSIPP(graph, heuristic, tad_exp.agents, filter_nodes=filter_nodes, use_flexibility=False)
result2 = maeder.run_search(delay_agent.origin.name, delay_agent.destination.name, delay_agent.measures.start_time, optimize_total_delay=False, find_first_path=False, 
                            redirect_stderr=f"{outdir}/stderr_@MAEDeR_Eurostar-{scen_num}.txt", 
                            redirect_stdout=f"{outdir}/stdout_@MAEDeR_Eurostar-{scen_num}.txt", 
                            write_fsipp_graph=f"{outdir}/fsipp_@MAEDeR_Eurostar_graph-{scen_num}.txt", 
                            store_fsipp_output=f"{outdir}/fsipp_@MAEDeR_Eurostar_search-{scen_num}.json")
print("Ran the @MAEDeR algorithm")
