import json

from generation.railways.block_graph import BlockGraph
from generation.railways.scenario import Scenario
from generation.railways.track_graph import TrackGraph
from generation.railways.train_agent import TrainAgent
from generation.util.types import GraphType

# TODO: discuss if we want this file, or keep TrackGraph and BlockGraph (railway specific classes) to the experiment files

def graph_from_file(file) -> BlockGraph:
    track_graph = TrackGraph.read_graph(file)
    block_graph = BlockGraph.from_track_graph(track_graph)
    return block_graph

def scenario_from_file(file, graph: GraphType, agent_cls=TrainAgent):
    with open(file) as f:
        data = json.load(f)
    scenario = Scenario(data, graph, agent_cls)
    return scenario
