import os
import sys

import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "experiments", "mapf"))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__))))

from flexsipp.graphs.fsipp import FSIPP
from flexsipp.graphs.graph import Node
from flexsipp.util.intervals import UnsafeInterval
from experiments.mapf.read_experiment import create_mapf_instance_from_paths


class TestCorridorExample(unittest.TestCase):

    def test_corridor_example(self):
        start_time = 0
        end_time = 12
        graph, agents = create_mapf_instance_from_paths(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "corridor_test", "corridor.map"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "corridor_test", "paths.txt"),
            end_time)
        heuristic = {node.name: 0 for node in graph.nodes.values()}
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].by_agent, agents[1])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].start, 0)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].end, 1)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].by_agent, agents[2])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].start, 1)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].end, 2)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].by_agent, agents[3])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].start, 3)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].end, 4)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].by_agent, agents[4])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].start, 2)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].end, 3)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].by_agent, agents[1])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].start, 3)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].end, 4)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].by_agent, agents[2])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].start, 4)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].end, 5)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].by_agent, agents[3])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].start, 6)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].end, end_time)
        
        rerouting_agent0 = agents[3]
        old_nodes = graph.nodes.copy()
        old_edges = graph.edges.copy()
        original_arrival0 = rerouting_agent0.destination.unsafe_intervals[-1].start
        start0 = 10
        graph.filter_out_agent(rerouting_agent0)
        flexSIPP0 = FSIPP(graph, heuristic, agents)
        result0 = flexSIPP0.run_search(rerouting_agent0.origin.name, rerouting_agent0.destination.name, start0, graph.global_end_time, optimize_total_delay=False)
        
        self.assertEqual(len(result0.found_routes), 0)
        graph.update_unsafe_intervals(new_path=(rerouting_agent0, [(rerouting_agent0.destination, (0, graph.global_end_time))], start0), minimum_delays={})
        self.assertEqual(rerouting_agent0.destination.unsafe_intervals[-1].start, original_arrival0)
        for node in graph.nodes:
            self.assertEqual(graph.nodes[node].unsafe_intervals, old_nodes[node].unsafe_intervals)
        for i in range(len(graph.edges)):
            self.assertEqual(graph.edges[i].unsafe_intervals, old_edges[i].unsafe_intervals)
        
        rerouting_agent1 = agents[1]
        graph.filter_out_agent(rerouting_agent1)
        flexSIPP1 = FSIPP(graph, heuristic, agents)
        result1 = flexSIPP1.run_search(rerouting_agent1.origin.name, rerouting_agent1.destination.name, start_time, graph.global_end_time, optimize_total_delay=False)

        ##### Test First FlexSIPP run #####
        self.assertEqual(len(result1.found_routes), 3)
        atf1, res1 = result1.found_routes[0]
        self.assertEqual(atf1[1], 0) # alpha
        self.assertEqual(atf1[2], 1) # beta
        self.assertDictEqual(res1["delays"], {1: [], 2: [], 3: [], 4: [], 5: []})
        self.assertEqual(result1.found_routes[0], result1.found_routes[1])
        atf2, res2 = result1.found_routes[2]
        self.assertEqual(atf2[1], 1) # alpha
        self.assertEqual(atf2[2], 2) # beta
        self.assertDictEqual(res2["delays"], {1: [], 2: [(graph.nodes["(1,1)"], 0, 0, 1)], 3: [], 4: [], 5: []})
        
        ## Paths
        self.assertEqual(len(result1.unique_path_eatfs["(0,1)->(1,1)->(2,1)->(3,1)->(3,2)"]), 2)
        self.assertIn("(0,1)->(1,1)->(2,1)->(3,1)->(3,2)", result1.unique_path_eatfs)
        # First path safe in [0,1>
        self.assertEqual(result1.unique_path_eatfs["(0,1)->(1,1)->(2,1)->(3,1)->(3,2)"][0][1], 0)
        self.assertEqual(result1.unique_path_eatfs["(0,1)->(1,1)->(2,1)->(3,1)->(3,2)"][0][2], 1)
        # Second path safe in [1,2>
        self.assertEqual(result1.unique_path_eatfs["(0,1)->(1,1)->(2,1)->(3,1)->(3,2)"][1][1], 1)
        self.assertEqual(result1.unique_path_eatfs["(0,1)->(1,1)->(2,1)->(3,1)->(3,2)"][1][2], 2)
        ###################################
        
        actual_delay1 = 1
        res_atf1, new_route1, minimum_delays1 = result1.get_fastest_route(float(actual_delay1), agents, discrete=True, print_agent_delays=False)
        del minimum_delays1[rerouting_agent1]
        graph.update_unsafe_intervals(new_path=(rerouting_agent1, new_route1, actual_delay1), minimum_delays=minimum_delays1)
        
        print(f"Agent {rerouting_agent1} is delayed at time {actual_delay1} and has new path {'-'.join([node[0].name for node in new_route1 if isinstance(node[0], Node)])} with atf {res_atf1} that delays agent {[k for k, v in minimum_delays1.items() if v]} with route {'-'.join([node.name for node in [k for k, v in minimum_delays1.items() if v][0].route if isinstance(node, Node)])} at nodes {[f'{n}: {time}' for k, v in minimum_delays1.items() for n, time in v.items() if isinstance(n, Node)]}")

        ##### Test First FlexSIPP update #####
        # Found path uses flexibility
        self.assertEqual(new_route1, result1.found_routes[2][1]["route"])
        self.assertEqual(res_atf1[1], 1)
        self.assertEqual(res_atf1[2], 2)
        self.assertIn(graph.nodes["(1,1)"], minimum_delays1[agents[2]])
        self.assertIn(graph.nodes["(0,0)"], minimum_delays1[agents[2]])

        # Safe interval updates
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].by_agent, agents[1])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].start, 0)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].end, 2)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].by_agent, agents[2])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].start, 2)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].end, 3)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].by_agent, agents[3])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].start, 3)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].end, 4)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].by_agent, agents[4])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].start, 2)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].end, 3)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].by_agent, agents[1])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].start, 4)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].end, 5)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].by_agent, agents[2])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].start, 5)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].end, 6)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].by_agent, agents[3])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].start, 6)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].end, end_time)
        ###################################

        rerouting_agent2 = agents[2]
        graph.filter_out_agent(rerouting_agent2)
        flexSIPP2 = FSIPP(graph, heuristic, agents)
        result2 = flexSIPP2.run_search(rerouting_agent2.origin.name, rerouting_agent2.destination.name, start_time, graph.global_end_time, optimize_total_delay=False)

        ##### Test Second FlexSIPP run #####
        self.assertEqual(len(result2.found_routes), 3)
        atf1, res1 = result2.found_routes[0]
        self.assertEqual(atf1[1], 1) # alpha
        self.assertEqual(atf1[2], 2) # beta
        self.assertDictEqual(res1["delays"], {1: [], 2: [], 3: [], 4: [], 5: []})
        self.assertEqual(result2.found_routes[0], result2.found_routes[1])
        atf2, res2 = result2.found_routes[2]
        self.assertEqual(atf2[1], 2) # alpha
        self.assertEqual(atf2[2], 8) # beta

        self.assertDictEqual(res2["delays"], {1: [], 2: [], 3: [(graph.nodes["(0,1)"], 0, 0, 6)], 4: [], 5: []})

        ## Paths
        self.assertIn("(0,0)->(0,1)->(1,1)->(2,1)->(3,1)->(3,0)", result2.unique_path_eatfs)
        self.assertEqual(len(result2.unique_path_eatfs["(0,0)->(0,1)->(1,1)->(2,1)->(3,1)->(3,0)"]), 2)
        # First path safe in [0,1>
        self.assertEqual(result2.unique_path_eatfs["(0,0)->(0,1)->(1,1)->(2,1)->(3,1)->(3,0)"][0][1], 1)
        self.assertEqual(result2.unique_path_eatfs["(0,0)->(0,1)->(1,1)->(2,1)->(3,1)->(3,0)"][0][2], 2)
        # Second path safe in [1,2>
        self.assertEqual(result2.unique_path_eatfs["(0,0)->(0,1)->(1,1)->(2,1)->(3,1)->(3,0)"][1][1], 2)
        self.assertEqual(result2.unique_path_eatfs["(0,0)->(0,1)->(1,1)->(2,1)->(3,1)->(3,0)"][1][2], 8)
        ###################################

        actual_delay2 = 4
        res_atf2, new_route2, minimum_delays2 = result2.get_fastest_route(float(actual_delay2), agents, discrete=True, print_agent_delays=False)
        del minimum_delays2[rerouting_agent2]
        graph.update_unsafe_intervals(new_path=(rerouting_agent2, new_route2, actual_delay2), minimum_delays=minimum_delays2)
        
        print(f"Agent {rerouting_agent2} is delayed at time {actual_delay2} and has new path {'-'.join([node[0].name for node in new_route2 if isinstance(node[0], Node)])} with atf {res_atf2} that delays agent {[k for k, v in minimum_delays2.items() if v]} with route {'-'.join([node.name for node in [k for k, v in minimum_delays2.items() if v][0].route if isinstance(node, Node)])} at nodes {[f'{n}: {time}' for k, v in minimum_delays2.items() for n, time in v.items() if isinstance(n, Node)]}")

        ##### Test Second FlexSIPP update #####
        # Found path uses flexibility
        self.assertEqual(new_route2, result2.found_routes[2][1]["route"])
        self.assertEqual(res_atf2[1], 2)
        self.assertEqual(res_atf2[2], 8)
        self.assertIn(graph.nodes["(0,1)"], minimum_delays2[agents[3]])
        self.assertIn(graph.nodes["(0,2)"], minimum_delays2[agents[3]])

        # Safe interval updates
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].by_agent, agents[1])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].start, 0)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].end, 2)
        self.assertEqual(graph.nodes["(0,0)"].unsafe_intervals[0].by_agent, agents[2])
        self.assertEqual(graph.nodes["(0,0)"].unsafe_intervals[0].start, 0)
        self.assertEqual(graph.nodes["(0,0)"].unsafe_intervals[0].end, 5)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].by_agent, agents[2])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].start, 5)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].end, 6)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].by_agent, agents[3])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].start, 6)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].end, 7)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].by_agent, agents[4])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].start, 2)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].end, 3)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].by_agent, agents[1])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].start, 4)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].end, 5)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].by_agent, agents[2])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].start, 8)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].end, 9)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].by_agent, agents[3])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].start, 9)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].end, 12)
        ###################################

        rerouting_agent3 = agents[4]
        graph.filter_out_agent(rerouting_agent3)
        flexSIPP3 = FSIPP(graph, heuristic, agents)
        result3 = flexSIPP3.run_search(rerouting_agent3.origin.name, rerouting_agent3.destination.name, start_time, graph.global_end_time, optimize_total_delay=False)

        ##### Test Second FlexSIPP run #####
        self.assertEqual(len(result3.found_routes), 3)
        atf1, res1 = result3.found_routes[2]
        self.assertEqual(atf1[1], 3) # alpha
        self.assertEqual(atf1[2], 6) # beta
        self.assertDictEqual(res1["delays"], {1: [(graph.nodes["(3,1)"], 0, 0, 3)], 2: [], 3: [], 4: [], 5: []})
        self.assertEqual(result3.found_routes[0], result3.found_routes[1])
        ###################################

        actual_delay3 = 4
        res_atf3, new_route3, minimum_delays3 = result3.get_fastest_route(float(actual_delay3), agents, discrete=True, print_agent_delays=False)
        del minimum_delays3[rerouting_agent3]
        graph.update_unsafe_intervals(new_path=(rerouting_agent3, new_route3, actual_delay3), minimum_delays=minimum_delays3)
        print(f"Agent {rerouting_agent3} is delayed at time {actual_delay3} and has new path {'-'.join([node[0].name for node in new_route3 if isinstance(node[0], Node)])} with atf {res_atf3} that delays agent {[k for k, v in minimum_delays3.items() if v]} with route {'-'.join([node.name for node in [k for k, v in minimum_delays3.items() if v][0].route if isinstance(node, Node)])} at nodes {[f'{n}: {time}' for k, v in minimum_delays3.items() for n, time in v.items() if isinstance(n, Node)]}")

        ##### Test Third FlexSIPP update #####
        # Found path uses flexibility
        self.assertEqual(new_route3, result3.found_routes[0][1]["route"])
        self.assertEqual(res_atf3[1], 3)
        self.assertEqual(res_atf3[2], 6)
        self.assertIn(graph.nodes["(3,1)"], minimum_delays3[agents[1]])

        # Safe interval updates
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].by_agent, agents[1])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].start, 0)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[0].end, 2)
        self.assertEqual(graph.nodes["(0,0)"].unsafe_intervals[0].by_agent, agents[2])
        self.assertEqual(graph.nodes["(0,0)"].unsafe_intervals[0].start, 0)
        self.assertEqual(graph.nodes["(0,0)"].unsafe_intervals[0].end, 5)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].by_agent, agents[2])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].start, 5)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[1].end, 6)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].by_agent, agents[3])
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].start, 6)
        self.assertEqual(graph.nodes["(0,1)"].unsafe_intervals[2].end, 7)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].by_agent, agents[4])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].start, 5)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[0].end, 6)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].by_agent, agents[1])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].start, 6)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[1].end, 7)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].by_agent, agents[2])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].start, 8)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[2].end, 9)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].by_agent, agents[3])
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].start, 9)
        self.assertEqual(graph.nodes["(3,1)"].unsafe_intervals[3].end, 12)
        ###################################

        rerouting_agent4 = agents[3]
        old_nodes = graph.nodes.copy()
        old_edges = graph.edges.copy()
        original_arrival = rerouting_agent4.destination.unsafe_intervals[-1].start
        start4 = 10
        graph.filter_out_agent(rerouting_agent4)
        flexSIPP4 = FSIPP(graph, heuristic, agents)
        result4 = flexSIPP4.run_search(rerouting_agent4.origin.name, rerouting_agent4.destination.name, start4, graph.global_end_time, optimize_total_delay=False)
        
        self.assertEqual(len(result4.found_routes), 0)
        graph.update_unsafe_intervals(new_path=(rerouting_agent4, [(rerouting_agent4.destination, (0, graph.global_end_time))], start4), minimum_delays={})
        self.assertEqual(rerouting_agent4.destination.unsafe_intervals[-1].start, original_arrival)
        for node in graph.nodes:
            self.assertEqual(graph.nodes[node].unsafe_intervals, old_nodes[node].unsafe_intervals)
        for i in range(len(graph.edges)):
            self.assertEqual(graph.edges[i].unsafe_intervals, old_edges[i].unsafe_intervals)
            

if __name__ == '__main__':
    unittest.main()
