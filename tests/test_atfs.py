import os
import unittest
from copy import copy
from flexsipp.graphs.fsipp import FSIPP

from experiments.railways.flexsipp_railways.generate import graph_from_file, scenario_from_file
from experiments.railways.flexsipp_railways.train_agents.train_agent_limited_flexibility import train_agent_limited_flexibility_generator

class TestFSIPP(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        bg = graph_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "railways", "location_test.json"))
        scenario = scenario_from_file(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "railways", "scenario_test.json"),
            bg,
            train_agent_limited_flexibility_generator(0, 0))
        scenario.process()
        heuristic = {node.name: 0 for node in bg.nodes.values()}
        new_agent = copy(scenario.agents["1"])
        new_agent.id = -1
        cls.flexSIPP = FSIPP(scenario.fsipp(new_agent), heuristic, scenario.agents)

    def test_atf_node_reference(self):
        safe_node_interval_ids: set[int] = {si.index for node in self.flexSIPP.nodes for si in node.safe_intervals}
        for atf in self.flexSIPP.atfs:
            self.assertTrue(atf.from_id in safe_node_interval_ids)
            self.assertTrue(atf.to_id in safe_node_interval_ids)

class TestLimitedFlexibilityGenerator(unittest.TestCase):

    @staticmethod
    def setUpScenario(max_buffer, max_crt):
        bg = graph_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "railways", "location_test.json"))
        scenario = scenario_from_file(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "railways", "scenario_test.json"),
            bg,
            train_agent_limited_flexibility_generator(max_buffer, max_crt))
        scenario.process()
        heuristic = {node.name: 0 for node in bg.nodes.values()}
        new_agent = copy(scenario.agents["1"])
        new_agent.id = -1
        return FSIPP(scenario.fsipp(new_agent), heuristic, scenario.agents)

    def test_no_flexibility(self):
        flexSIPP = self.setUpScenario(0, 0)
        for atf in flexSIPP.atfs:
            self.assertEqual(atf.crt_before, 0)
            self.assertEqual(atf.crt_after, 0)
            self.assertEqual(atf.buffer_after, 0)

if __name__ == '__main__':
    unittest.main()
