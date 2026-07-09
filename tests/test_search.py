import os
import unittest
from copy import copy

from flexsipp.graphs.fsipp import FSIPP
from experiments.railways.flexsipp_railways.generate import graph_from_file, scenario_from_file
from experiments.railways.flexsipp_railways.train_agents.train_agent_limited_flexibility import train_agent_limited_flexibility_generator


class TestSearch(unittest.TestCase):

    def setUpScenario(self, max_buffer, max_crt):
        bg = graph_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "railways", "location_test.json"))
        scenario = scenario_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "railways", "scenario_test.json"), bg, train_agent_limited_flexibility_generator(max_buffer, max_crt))
        scenario.process()
        heuristic = {node.name: 0 for node in bg.nodes.values()}
        self.new_agent = copy(scenario.agents["1"])
        self.new_agent.id = -1
        self.flexSIPP = FSIPP(scenario.fsipp(self.new_agent), heuristic, scenario.agents)
        self.scenario = scenario

    def test_no_flexibility(self):
        self.setUpScenario(0, 0)
        result = self.flexSIPP.run_search(self.new_agent.origin.name, self.new_agent.destination.name, self.new_agent.measures.start_time)
        self.assertEqual(len(result.unique_path_eatfs), 1)
        self.assertIn('u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A', result.unique_path_eatfs)
        self.assertEqual(len(result.unique_path_eatfs['u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A']), 2)
        self.assertEqual(result.unique_path_eatfs['u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A'][0][1], 3)
        self.assertEqual(result.unique_path_eatfs['u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A'][0][2], 4)

class TestSearchEndTime(unittest.TestCase):

    def test_default_end_time(self):
        bg = graph_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "railways", "location_test.json"), global_end_time=None)
        scenario = scenario_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "railways", "scenario_test.json"), bg)
        self.assertEqual(scenario.g.global_end_time, 36)
        
        scenario.process()
        heuristic = {node.name: 0 for node in bg.nodes.values()}
        self.new_agent = copy(scenario.agents["1"])
        self.new_agent.id = -1
        self.flexSIPP = FSIPP(scenario.fsipp(self.new_agent), heuristic, scenario.agents)
        self.scenario = scenario
        result = self.flexSIPP.run_search(self.new_agent.origin.name, self.new_agent.destination.name, self.new_agent.measures.start_time)
        self.assertEqual(len(result.found_routes), 5)
        self.assertEqual(len(result.unique_routes), 2)
        self.assertEqual(len(result.unique_path_eatfs), 1)
        self.assertIn('u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A', result.unique_path_eatfs)
        self.assertEqual(len(result.unique_path_eatfs['u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A']), 3)
        self.assertEqual(result.unique_path_eatfs['u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A'][0][1], 3)
        self.assertEqual(result.unique_path_eatfs['u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A'][0][2], 4)

    def test_custom_end_time(self):
        end_time = 20
        bg = graph_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "railways", "location_test.json"), global_end_time=end_time)
        scenario = scenario_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "railways", "scenario_test.json"), bg)
        self.assertEqual(scenario.g.global_end_time, end_time)
        
        scenario.process()
        heuristic = {node.name: 0 for node in bg.nodes.values()}
        self.new_agent = copy(scenario.agents["1"])
        self.new_agent.id = -1
        self.flexSIPP = FSIPP(scenario.fsipp(self.new_agent), heuristic, scenario.agents)
        self.scenario = scenario
        result = self.flexSIPP.run_search(self.new_agent.origin.name, self.new_agent.destination.name, self.new_agent.measures.start_time)
        self.assertEqual(len(result.found_routes), 3)
        self.assertEqual(len(result.unique_routes), 1)
        self.assertEqual(len(result.unique_path_eatfs), 1)
        self.assertIn('u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A', result.unique_path_eatfs)
        self.assertEqual(len(result.unique_path_eatfs['u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A']), 2)
        self.assertEqual(result.unique_path_eatfs['u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A'][0][1], 3)
        self.assertEqual(result.unique_path_eatfs['u|A->w|A->s1|A->s2|A->s3|A->s4|A->s5|A->sv|A'][0][2], 4)

if __name__ == '__main__':
    unittest.main()
