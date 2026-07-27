import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "experiments", "mapf"))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__))))

from flexsipp.graphs.fsipp import FSIPP
from flexsipp.graphs.graph import Node
from experiments.mapf.read_experiment import create_mapf_instance_from_paths

class TestTippingPoints(unittest.TestCase):
    def test_any_start_time_plans(self):
        """Compute any-start-time for agent 2, not optimized on total delay so will prioritize agent 2."""
        start_time = 0
        end_time = 12
        graph, agents = create_mapf_instance_from_paths(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "grid_test", "grid.map"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "grid_test", "paths.txt"),
            end_time)
        delay_agent = agents[2]
        original_arrival = delay_agent.destination.unsafe_intervals[-1].start
        self.assertEqual(original_arrival, 7)
        
        heuristic = {node.name: 0 for node in graph.nodes.values()}
        graph.filter_out_agent(delay_agent)
        flexSIPP_atsipp = FSIPP(graph, heuristic, agents)

        # Compute any-start-time plan
        result_optimize_agent = flexSIPP_atsipp.run_search(delay_agent.origin.name, delay_agent.destination.name, start_time, graph.global_end_time, optimize_total_delay=False, redirect_stderr="stderr_grid_test_any-start-time-plan.txt")
        self.assertEqual(len(result_optimize_agent.unique_path_eatfs), 1)
        self.assertEqual(len(result_optimize_agent.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(3,1)->(4,1)->(5,1)']), 4)
        self.assertEqual(result_optimize_agent.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(3,1)->(4,1)->(5,1)'][0], [float('-inf'), 0, 1, 5])
        self.assertEqual(result_optimize_agent.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(3,1)->(4,1)->(5,1)'][1], [float('-inf'), 1, 3, 5])
        self.assertEqual(result_optimize_agent.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(3,1)->(4,1)->(5,1)'][2], [float('-inf'), 3, 4, 5])
        self.assertEqual(result_optimize_agent.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(3,1)->(4,1)->(5,1)'][3], [float('-inf'), 4, 7, 5])
        self.assertEqual(result_optimize_agent.found_routes[0][0], [float('-inf'), 0, 1, 5])
        self.assertGreaterEqual(len(result_optimize_agent.found_routes[0][1]["delays"][1]), 1)
        self.assertEqual(result_optimize_agent.found_routes[2][0], [float('-inf'), 1, 3, 5])
        self.assertGreaterEqual(len(result_optimize_agent.found_routes[2][1]["delays"][1]), 1)
        self.assertEqual(result_optimize_agent.found_routes[3][0], [float('-inf'), 3, 4, 5])
        self.assertGreaterEqual(len(result_optimize_agent.found_routes[3][1]["delays"][1]), 1)
        self.assertEqual(result_optimize_agent.found_routes[4][0], [float('-inf'), 4, 7, 5])
        self.assertEqual(result_optimize_agent.found_routes[4][1]["delays"], {1: [], 2: []})
        
        # Tipping point is the point after which agent 2 should just wait for agent 1
        tipping_points = result_optimize_agent.find_tipping_points(delay_agent, original_arrival, agents, discrete=True, optimize_total_delay=False, print_tipping_points=True)
        self.assertEqual(len(tipping_points), 1)
        self.assertEqual(tipping_points[0][0], 4)
        self.assertEqual(tipping_points[0][1][agents[1]], (graph.nodes["(4,1)"], 4))
        self.assertEqual(tipping_points[0][2][agents[1]][graph.nodes["(3,1)"]], 8)
        atf, route, _, _ = result_optimize_agent.get_fastest_route(delay_agent, original_arrival, tipping_points[0][0], agents, discrete=True, optimize_total_delay=False)
        self.assertEqual(atf, [float("-inf"), 4, 7, 5])
        # Check the nodes in the route
        self.assertListEqual([x[0] for x in route if isinstance(x[0], Node)], [graph.nodes["(0,1)"], graph.nodes["(1,1)"], graph.nodes["(2,1)"], graph.nodes["(3,1)"], graph.nodes["(4,1)"], graph.nodes["(5,1)"]])
        
        # When objective is to minimize the total delay, agent 2 can still go first until 
        # Original route for agent 2 took longer route, so delaying agent 1 a little still improves total delay.
        tipping_points_start_opt_delay = result_optimize_agent.find_tipping_points(delay_agent, original_arrival, agents, discrete=True, optimize_total_delay=True, print_tipping_points=True)
        self.assertEqual(len(tipping_points_start_opt_delay), 1)
        self.assertEqual(tipping_points_start_opt_delay[0][0], 0.5)
        self.assertEqual(tipping_points_start_opt_delay[0][1][agents[1]], (graph.nodes["(4,1)"], 4))
        self.assertEqual(tipping_points_start_opt_delay[0][2][agents[1]][graph.nodes["(3,1)"]], 4.5)
        atf, route, _, _ = result_optimize_agent.get_fastest_route(delay_agent, original_arrival, tipping_points_start_opt_delay[0][0], agents)
        self.assertEqual(atf, [float("-inf"), 0, 1, 5])
        # Check the nodes in the route
        self.assertListEqual([x[0] for x in route if isinstance(x[0], Node)], [graph.nodes["(0,1)"], graph.nodes["(1,1)"], graph.nodes["(2,1)"], graph.nodes["(3,1)"], graph.nodes["(4,1)"], graph.nodes["(5,1)"]])

        actual_delay = 1
        # If the delay is 1 and we don't optimize total delay, then delay agent 2
        res_atf, new_route, minimum_delays, tipping_loc = result_optimize_agent.get_fastest_route(delay_agent, original_arrival, float(actual_delay), agents, discrete=True, print_agent_delays=False, optimize_total_delay=False)
        self.assertListEqual(res_atf, [float("-inf"), 1, 3, 5])
        # Tipping point ((4,1), 4)
        self.assertEqual(tipping_loc[agents[1]][0], graph.nodes["(4,1)"])
        self.assertEqual(tipping_loc[agents[1]][1], 4)
        # Agent 1 must wait in its origin (4, 0) for 5 timesteps
        self.assertEqual(minimum_delays[agents[1]][graph.nodes["(4,0)"]], 5)
        # Agent 2 takes shortest route
        self.assertListEqual([x[0] for x in new_route if isinstance(x[0], Node)], [graph.nodes["(0,1)"], graph.nodes["(1,1)"], graph.nodes["(2,1)"], graph.nodes["(3,1)"], graph.nodes["(4,1)"], graph.nodes["(5,1)"]])
        
        # If the delay is 1 and we do optimize total delay, wait for agent 2
        res_atf, new_route, minimum_delays, tipping_loc = result_optimize_agent.get_fastest_route(delay_agent, original_arrival, float(actual_delay), agents, discrete=True, print_agent_delays=False, optimize_total_delay=True)
        self.assertListEqual(res_atf, [float("-inf"), 4, 7, 5])
        self.assertDictEqual(tipping_loc, {})
        # Agent 1 does not have to wait
        self.assertDictEqual(minimum_delays[agents[1]], {})
        self.assertListEqual([x[0] for x in new_route if isinstance(x[0], Node)], [graph.nodes["(0,1)"], graph.nodes["(1,1)"], graph.nodes["(2,1)"], graph.nodes["(3,1)"], graph.nodes["(4,1)"], graph.nodes["(5,1)"]])
        
        # If the delay is too large, then agent 1 must just wait for agent 2 to optimize the delay
        actual_delay = 2 
        res_atf, new_route, minimum_delays, tipping_loc = result_optimize_agent.get_fastest_route(delay_agent, original_arrival, float(actual_delay), agents, discrete=True, print_agent_delays=False, optimize_total_delay=True)
        self.assertListEqual(res_atf, [float("-inf"), 4, 7, 5])
        self.assertDictEqual(tipping_loc, {})
        # Agent 1 does not have to wait
        self.assertDictEqual(minimum_delays[agents[1]], {})
        self.assertListEqual([x[0] for x in new_route if isinstance(x[0], Node)], [graph.nodes["(0,1)"], graph.nodes["(1,1)"], graph.nodes["(2,1)"], graph.nodes["(3,1)"], graph.nodes["(4,1)"], graph.nodes["(5,1)"]])


    def test_optimal_delay_any_start_time_plans(self):
        start_time = 0
        end_time = 12
        graph, agents = create_mapf_instance_from_paths(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "grid_test", "grid.map"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "grid_test", "paths.txt"),
            end_time)
        delay_agent = agents[2]
        original_arrival = delay_agent.destination.unsafe_intervals[-1].start
        self.assertEqual(original_arrival, 7)
        
        heuristic = {node.name: 0 for node in graph.nodes.values()}
        graph.filter_out_agent(delay_agent)
        flexSIPP = FSIPP(graph, heuristic, agents)

        # Compute any-start-time plan that is optimized for delay
        result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, start_time, graph.global_end_time, optimize_total_delay=True)
        self.assertEqual(len(result.unique_path_eatfs), 2)
        self.assertEqual(len(result.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(3,1)->(4,1)->(5,1)']), 1)
        self.assertListEqual(result.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(3,1)->(4,1)->(5,1)'][0], [float("-inf"), 5, 7, 5])
        self.assertEqual(len(result.unique_path_eatfs['(0,1)->(0,2)->(1,2)->(2,2)->(3,2)->(4,2)->(4,1)->(5,1)']), 1)
        self.assertEqual(result.unique_path_eatfs['(0,1)->(0,2)->(1,2)->(2,2)->(3,2)->(4,2)->(4,1)->(5,1)'][0], [float("-inf"), 0, 5, 7])
        
        tipping_points = result.find_tipping_points(delay_agent, original_arrival, agents, discrete=True, optimize_total_delay=True, print_tipping_points=True)
        self.assertEqual(len(tipping_points), 1)
        self.assertEqual(tipping_points[0][0], 3)
        self.assertEqual(tipping_points[0][1][agents[2]], (graph.nodes["(0,1)"], 3))
        self.assertEqual(tipping_points[0][2], {agents[1]: {}, agents[2]: {}})
       
    def test_with_heuristic(self):
        start_time = 0
        end_time = 12
        graph, agents = create_mapf_instance_from_paths(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "grid_test", "grid.map"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "grid_test", "paths.txt"),
            end_time)
        delay_agent = agents[2]
        original_arrival = delay_agent.destination.unsafe_intervals[-1].start
        self.assertEqual(original_arrival, 7)
        
        # Use a shortest path heuristic
        heuristic = graph.calculate_heuristic(delay_agent.destination)
        graph.filter_out_agent(delay_agent)
        flexSIPP = FSIPP(graph, heuristic, agents)

        # Compute any-start-time plan that is optimized for delay
        result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, start_time, graph.global_end_time, optimize_total_delay=True)
        self.assertEqual(len(result.unique_path_eatfs), 2)
        self.assertEqual(len(result.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(3,1)->(4,1)->(5,1)']), 1)
        self.assertListEqual(result.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(3,1)->(4,1)->(5,1)'][0], [float("-inf"), 4, 7, 5])
        self.assertEqual(len(result.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(2,2)->(2,1)->(3,1)->(4,1)->(5,1)']), 2)
        
        tipping_points = result.find_tipping_points(delay_agent, original_arrival, agents, discrete=True, optimize_total_delay=True, print_tipping_points=True)
        self.assertEqual(len(tipping_points), 1)
        self.assertEqual(tipping_points[0][0], 1.5)
        self.assertEqual(tipping_points[0][1][agents[2]], (graph.nodes["(0,1)"], 1.5))
        # No delays
        self.assertDictEqual(tipping_points[0][2], {agents[1]: {}, agents[2]: {}})
        tipping_points = result.find_tipping_points(delay_agent, original_arrival, agents, discrete=True, optimize_total_delay=False, print_tipping_points=True)

    def test_single_plan(self):
        # When not optimizing delay, find a different route
        start_time = 2
        end_time = 12
        optimal_delay = False
        graph, agents = create_mapf_instance_from_paths(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "grid_test", "grid.map"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "grid_test", "paths.txt"),
            end_time)
        delay_agent = agents[2]
        original_arrival = delay_agent.destination.unsafe_intervals[-1].start
        self.assertEqual(original_arrival, 7)
        
        heuristic = graph.calculate_heuristic(delay_agent.destination)
        graph.filter_out_agent(delay_agent)
        flexSIPP = FSIPP(graph, heuristic, agents)

        # Compute optimal single plan
        result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, start_time, graph.global_end_time, optimize_total_delay=optimal_delay, find_first_path=True, redirect_stderr="stderr_test_single-plan.txt")
        self.assertEqual(len(result.unique_routes), 1)
        self.assertEqual(len(result.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(3,1)->(4,1)->(5,1)']), 1)
        
        # Finds a route that does not influence agent 1
        res_atf, new_route, minimum_delays, tipping_loc = result.get_fastest_route(delay_agent, original_arrival, float(start_time), agents, discrete=True, print_agent_delays=False, optimize_total_delay=optimal_delay)
        self.assertEqual(res_atf, result.found_routes[0][0])
        self.assertEqual(new_route, result.found_routes[0][1]["route"])
        self.assertEqual(tipping_loc[agents[1]], (graph.nodes["(4,1)"], 4))
        self.assertEqual(minimum_delays[agents[1]][graph.nodes["(4,0)"]], 6)

    def test_single_plan_optimal_delay(self):
        # Single delay forces agent 2 to reroute for agent 1
        start_time = 1
        end_time = 12
        optimal_delay = True
        graph, agents = create_mapf_instance_from_paths(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "grid_test", "grid.map"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "grid_test", "paths.txt"),
            end_time)

        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[0].by_agent, agents[1])
        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[0].start, 3)
        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[0].end, 4)
        self.assertEqual(graph.nodes["(4,1)"].unsafe_intervals[0].by_agent, agents[1])
        self.assertEqual(graph.nodes["(4,1)"].unsafe_intervals[0].start, 1)
        self.assertEqual(graph.nodes["(4,1)"].unsafe_intervals[0].end, 2)

        delay_agent = agents[2]
        original_arrival = delay_agent.destination.unsafe_intervals[-1].start
        self.assertEqual(original_arrival, 7)

        heuristic = graph.calculate_heuristic(delay_agent.destination)
        graph.filter_out_agent(delay_agent)
        flexSIPP = FSIPP(graph, heuristic, agents)

        # Compute optimal single plan
        result = flexSIPP.run_search(delay_agent.origin.name, delay_agent.destination.name, start_time, graph.global_end_time, optimize_total_delay=optimal_delay, find_first_path=True, redirect_stderr="stderr_test_single-plan_opt.txt")
        self.assertEqual(len(result.unique_routes), 1)
        self.assertEqual(len(result.unique_path_eatfs['(0,1)->(1,1)->(2,1)->(2,2)->(2,1)->(3,1)->(4,1)->(5,1)']), 1)
        
        # Since agent 1 was supposed to start at t=0, it is delayed by 1 if agent 2 start at t=1
        res_atf, new_route, minimum_delays, tipping_loc = result.get_fastest_route(delay_agent, original_arrival, float(start_time), agents, discrete=True, print_agent_delays=False, optimize_total_delay=optimal_delay)
        self.assertEqual(res_atf, result.found_routes[0][0])
        self.assertEqual(new_route, result.found_routes[0][1]["route"])
        self.assertEqual(tipping_loc[agents[1]], (graph.nodes["(4,1)"], 6))
        self.assertEqual(minimum_delays[agents[1]][graph.nodes["(4,1)"]], 1)
        self.assertEqual(minimum_delays[agents[1]][graph.nodes["(3,1)"]], 1)
        self.assertEqual(minimum_delays[agents[1]][graph.nodes["(2,1)"]], 1)
        
        del minimum_delays[delay_agent]
        graph.update_unsafe_intervals(new_path=(delay_agent, new_route, start_time), minimum_delays=minimum_delays)
        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[0].by_agent, agents[2])
        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[0].start, 3)
        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[0].end, 4)
        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[1].by_agent, agents[1])
        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[1].start, 4)
        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[1].end, 5)
        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[2].by_agent, agents[2])
        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[2].start, 5)
        self.assertEqual(graph.nodes["(2,1)"].unsafe_intervals[2].end, 6)
        # Agent 1 is now delayed and departs only at t=1
        self.assertEqual(graph.nodes["(4,1)"].unsafe_intervals[0].by_agent, agents[1])
        self.assertEqual(graph.nodes["(4,1)"].unsafe_intervals[0].start, 2)
        self.assertEqual(graph.nodes["(4,1)"].unsafe_intervals[0].end, 3)
        self.assertEqual(graph.nodes["(4,1)"].unsafe_intervals[1].by_agent, agents[2])
        self.assertEqual(graph.nodes["(4,1)"].unsafe_intervals[1].start, 7)
        self.assertEqual(graph.nodes["(4,1)"].unsafe_intervals[1].end, 8)

if __name__ == '__main__':
    unittest.main()
