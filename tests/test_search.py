import unittest
from copy import copy

from flexsipp.generate import graph_from_file, scenario_from_file
from flexsipp.graphs.fsipp import FSIPP
from flexsipp.railways.train_agents.train_agent_limited_flexiblity import train_agent_limited_flexibility_generator

class TestSearch(unittest.TestCase):

    def setUpScenario(self, max_buffer, max_crt):
        bg = graph_from_file("location_test.json")
        scenario = scenario_from_file("scenario_test.json", bg, train_agent_limited_flexibility_generator(max_buffer, max_crt))
        scenario.process()
        heuristic = {node.name: 0 for node in bg.nodes.values()}
        self.new_agent = copy(scenario.agents[0])
        self.new_agent.id = -1
        self.flexSIPP = FSIPP(scenario.fsipp(self.new_agent), heuristic)
        self.scenario = scenario

    def test_no_flexibility(self):
        self.setUpScenario(0, 0)
        result = self.flexSIPP.run_search(1000, self.new_agent.origin.name, self.new_agent.destination.name, self.new_agent.measures.start_time)
        print(result)

if __name__ == '__main__':
    unittest.main()
