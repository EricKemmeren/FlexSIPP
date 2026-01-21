from attr import dataclass

from generation.agent import Agent


@dataclass
class PlottingInfo:
    start_time: float = 0.0
    end_time: float = 0.0

class PlottingStore(object):
    def __init__(self):
        super().__init__()
        self.plotting_info: dict[Agent, PlottingInfo] = {}

    def add_start_time(self, agent: Agent, start_time: float):
        if agent not in self.plotting_info:
            self.plotting_info[agent] = PlottingInfo()
        self.plotting_info[agent].start_time = start_time

    def add_end_time(self, agent: Agent, end_time: float):
        if agent not in self.plotting_info:
            self.plotting_info[agent] = PlottingInfo()
        self.plotting_info[agent].end_time = end_time
