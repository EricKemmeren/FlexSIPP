import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "experiments", "mapf"))

from flexsipp.graphs.fsipp import FSIPP
from flexsipp.util.intervals import UnsafeInterval
from experiments.mapf.read_experiment import create_mapf_instance_from_paths


class TestWarehouseExample(unittest.TestCase):

    def test_warehouse_example(self):
        start_time = 0
        end_time = 12
        graph, agents = create_mapf_instance_from_paths(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "example_warehouse", "warehouse.map"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "example_warehouse", "paths.txt"),
            end_time)
        # Agent 1 (top left) breaks down, and is unable to move from (0,0)
        broken_down_agent = agents[1]
        self.assertEqual(broken_down_agent.origin, graph.nodes["(0,0)"])
        graph.filter_out_agent(broken_down_agent)
        graph.nodes["(0,0)"].add_unsafe_interval(UnsafeInterval(0.1, graph.global_end_time, 0, broken_down_agent, 0))

        # The route of Agent 2 is not not possible anymore, we should find a new route for this agent
        rerouting_agent = agents[2]
        original_arrival_time_reroute = rerouting_agent.destination.unsafe_intervals[-1].start

        # Filter out unsafe intervals of Agent 2 because it will find a new route
        graph.filter_out_agent(rerouting_agent)
        
        # Agent 4 has feasibility=8 at location (4,0) = 6th step in its route
        feasibility_agent = agents[4]
        self.assertEqual(feasibility_agent._get_local_flexibility(feasibility_agent.route[6]), (8,0))

        # Don't use a heuristic, set it to 0 for every node
        heuristic = {node.name: 0 for node in graph.nodes.values()}

        flexSIPP = FSIPP(graph, heuristic, agents)
        result = flexSIPP.run_search(rerouting_agent.origin.name, rerouting_agent.destination.name, start_time, graph.global_end_time, optimize_total_delay=False)
        
        self.assertIn("(0,2)->(1,2)->(2,2)->(3,2)->(3,1)->(3,0)->(2,0)->(1,0)", result.unique_path_eatfs)
        self.assertEqual(len(result.unique_path_eatfs["(0,2)->(1,2)->(2,2)->(3,2)->(3,1)->(3,0)->(2,0)->(1,0)"]), 4)

        # First path safe in (0,1)
        self.assertEqual(result.unique_path_eatfs["(0,2)->(1,2)->(2,2)->(3,2)->(3,1)->(3,0)->(2,0)->(1,0)"][0][1], 0)
        self.assertEqual(result.unique_path_eatfs["(0,2)->(1,2)->(2,2)->(3,2)->(3,1)->(3,0)->(2,0)->(1,0)"][0][2], 1)
        # Second path safe in (1,3)
        self.assertEqual(result.unique_path_eatfs["(0,2)->(1,2)->(2,2)->(3,2)->(3,1)->(3,0)->(2,0)->(1,0)"][1][1], 1)
        self.assertEqual(result.unique_path_eatfs["(0,2)->(1,2)->(2,2)->(3,2)->(3,1)->(3,0)->(2,0)->(1,0)"][1][2], 3)
        # Third path safe in (3,4)
        self.assertEqual(result.unique_path_eatfs["(0,2)->(1,2)->(2,2)->(3,2)->(3,1)->(3,0)->(2,0)->(1,0)"][2][1], 3)
        self.assertEqual(result.unique_path_eatfs["(0,2)->(1,2)->(2,2)->(3,2)->(3,1)->(3,0)->(2,0)->(1,0)"][2][2], 4)
        # Fourth path safe in (4,5)
        self.assertEqual(result.unique_path_eatfs["(0,2)->(1,2)->(2,2)->(3,2)->(3,1)->(3,0)->(2,0)->(1,0)"][3][1], 4)
        self.assertEqual(result.unique_path_eatfs["(0,2)->(1,2)->(2,2)->(3,2)->(3,1)->(3,0)->(2,0)->(1,0)"][3][2], 5)

        tipping_points = result.find_tipping_points(agents, original_arrival_time=original_arrival_time_reroute, optimize_total_delay=False, print_tipping_points=True)
        self.assertEqual(len(tipping_points), 1)
        self.assertEqual(tipping_points[0][0], 4)

        optimal_start_time = result.find_tipping_points(agents, original_arrival_time=original_arrival_time_reroute, optimize_total_delay=True, print_tipping_points=True)
        self.assertEqual(len(optimal_start_time), 1)
        self.assertEqual(optimal_start_time[0][0], 1.5)


if __name__ == '__main__':
    unittest.main()
