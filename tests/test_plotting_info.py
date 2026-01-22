import unittest

from flexsipp.generate import graph_from_file, scenario_from_file


class TestPlottingInfo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        bg = graph_from_file("location_test.json")
        cls.scenario = scenario_from_file("scenario_test.json", bg)
        cls.scenario.process()

    def test_start_times(self):
        agent_1 = self.scenario.get_replanning_agent(1)

        node = self.scenario.g.nodes["w|A"]
        for edge in node.outgoing:
            pi = edge.plotting_info[agent_1]
            self.assertEqual(pi.start_time, 3)
            self.assertEqual(pi.end_time, 4)

if __name__ == '__main__':
    unittest.main()
