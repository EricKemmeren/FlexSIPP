import os
import sys
import random
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "experiments", "mapf"))

from experiments.mapf.read_experiment import create_mapf_instance_from_paths
from experiments.mapf.sequential_delay_experiment import get_delays_from_seed, repeated_delays

import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

class TestSequential(unittest.TestCase):
    def test_repeated_delays(self):
        random.seed(42)
        epsilon = 0.001
        number_agents = 20
        flex_parameter = 0
        max_delay = 100
        number_delays = 5
        optimize_delay = True

        location_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "maze1", "maze-128-128-1.map")
        scenario_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mapf", "maze1", "scen-even", f"maze-128-128-1-even-1-k{number_agents}_paths{'_' + flex_parameter if flex_parameter > 0 else ''}.txt")
        graph, agents = create_mapf_instance_from_paths(location_file, scenario_file, scenario_end_time=None)
        
        result_file = os.path.join(os.path.dirname(__file__), "sequential_test_output.json")
        input_delays = get_delays_from_seed(location_file, scenario_file, number_agents, scenario_end=None, max_delay=max_delay)
        executed_delays, result = repeated_delays(location_file, scenario_file, input_delays, number_delays, result_file, optimize_delay=optimize_delay, scenario_end=None, use_flexibility=True)
        # Ensure that the first five delays were executed 
        self.assertEqual(number_delays, len(executed_delays))
        self.assertEqual(input_delays[:number_delays], executed_delays)
        
        self.assertAlmostEqual(result["delay0"]["max_delay"], 20.511, places=2)
        self.assertEqual(result["delay0"]["delay_agent"], 7)
        self.assertEqual(result["delay0"]["delay_location"], "(29,67)")

        self.assertAlmostEqual(result["delay1"]["max_delay"], 29.989, places=2)
        self.assertEqual(result["delay1"]["delay_agent"], 2)
        self.assertEqual(result["delay1"]["delay_location"], "(74,127)")
        
        self.assertAlmostEqual(result["delay2"]["max_delay"], 37.571, places=2)
        self.assertEqual(result["delay2"]["delay_agent"], 9)
        self.assertEqual(result["delay2"]["delay_location"], "(35,75)")
        
        self.assertAlmostEqual(result["delay3"]["max_delay"], 48.826, places=2)
        self.assertEqual(result["delay3"]["delay_agent"], 17)
        self.assertEqual(result["delay3"]["delay_location"], "(65,52)")

        self.assertAlmostEqual(result["delay4"]["max_delay"], 48.826, places=2)
        self.assertEqual(result["delay4"]["delay_agent"], 19)
        self.assertEqual(result["delay4"]["delay_location"], "(12,93)")
        
        self.assertAlmostEqual(sum([result["delay0"]['arrival_times'][a]['arrival'][1] - result["delay0"]["initial_paths"][a]['arrival'][1] for a in agents]), 30.0, places=1)
        self.assertAlmostEqual(sum([result["delay1"]['arrival_times'][a]['arrival'][1] - result["delay0"]["initial_paths"][a]['arrival'][1] for a in agents]), 30.0, places=1)
        self.assertAlmostEqual(sum([result["delay2"]['arrival_times'][a]['arrival'][1] - result["delay0"]["initial_paths"][a]['arrival'][1] for a in agents]), 76.0, places=1)
        self.assertAlmostEqual(sum([result["delay3"]['arrival_times'][a]['arrival'][1] - result["delay0"]["initial_paths"][a]['arrival'][1] for a in agents]), 79.8, places=1)
        self.assertAlmostEqual(sum([result["delay4"]['arrival_times'][a]['arrival'][1] - result["delay0"]["initial_paths"][a]['arrival'][1] for a in agents]), 78.8, places=1)
        
        os.remove(result_file)
