import json

from .railways.block_graph import BlockGraph
from .railways.scenario import Scenario
from .railways.track_graph import TrackGraph
from .railways.train_agent import TrainAgent
from .util.types import GraphType

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
