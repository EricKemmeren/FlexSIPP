import json

from .block_graph import BlockGraph
from .scenario import Scenario
from .track_graph import TrackGraph
from .train_agent import TrainAgent
from flexsipp.util.types import GraphType

def graph_from_file(file) -> BlockGraph:
    track_graph = TrackGraph(file)
    block_graph = BlockGraph(track_graph)
    return block_graph

def scenario_from_file(file, graph: GraphType, agent_cls=TrainAgent):
    with open(file) as f:
        data = json.load(f)
    scenario = Scenario(data, graph, agent_cls)
    return scenario
