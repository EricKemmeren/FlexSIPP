import unittest
from copy import copy
from typing import Tuple

from generation.generate import graph_from_file, scenario_from_file
from generation.graphs.fsipp import FSIPP
from generation.graphs.graph import IntervalStore
from generation.util.intervals import Interval


class TestTrackGraph(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tg = graph_from_file("location_test.json").tg

    def test_general_track_graph(self):
        self.assertEqual(len(self.tg.nodes), 30, "In total 32 nodes")
        self.assertEqual(len(self.tg.edges), 32, "In total 34 edges")
        self.assertEqual(len(self.tg.signals), 24, "In total 24 signals")
        self.assertEqual(len(self.tg.stations), 4, "Should be 4 stations")

    def test_track_nodes(self):
        s1A = self.tg.nodes["s1A"]
        self.assertCountEqual(s1A.associated, [])
        self.assertCountEqual(s1A.opposites,  [self.tg.nodes["wB"]])
        self.assertEqual(len(s1A.incoming), 1)
        self.assertEqual(len(s1A.outgoing), 1)

    def test_track_edge(self):
        self.assertEqual(self.tg.nodes["uA"].outgoing[0].length,  100)
        self.assertEqual(self.tg.nodes["suA"].outgoing[0].length, 0)
        self.assertEqual(self.tg.nodes["wA"].outgoing[0].length, 100)
        self.assertEqual(self.tg.nodes["uB"].outgoing[0].length,  100)
        self.assertEqual(self.tg.nodes["suB"].outgoing[0].length, 0)
        self.assertEqual(self.tg.nodes["wB"].outgoing[0].length, 100)
        self.assertEqual(self.tg.nodes["wB"].outgoing[1].length, 100)
        self.assertEqual(self.tg.nodes["wB"].outgoing[0].associated[0],
                         self.tg.nodes["wB"].outgoing[1])
        self.assertEqual(self.tg.nodes["wB"].outgoing[1].associated[0],
                         self.tg.nodes["wB"].outgoing[0])

    def test_bumper_node(self):
        u_a = self.tg.nodes["uA"]
        self.assertEqual(u_a.direction, "A")
        self.assertCountEqual(u_a.opposites, [])
        self.assertCountEqual(u_a.associated, [self.tg.nodes["uB"]]) # TODO: is this wanted?
        self.assertEqual(len(u_a.outgoing), 1)
        self.assertEqual(len(u_a.incoming), 1)

    def test_switch_node(self):
        w_a  = self.tg.nodes["wA"]
        w_b = self.tg.nodes["wB"]
        self.assertEqual(len(w_a.outgoing), 1)
        self.assertEqual(len(w_a.incoming), 2)

        self.assertEqual(len(w_b.outgoing), 2)
        self.assertEqual(len(w_b.incoming), 1)

        self.assertCountEqual(w_a.opposites, [self.tg.nodes["suB"], self.tg.nodes["suHatB"]])
        self.assertCountEqual(w_b.opposites, [self.tg.nodes["s1A"]])

        self.assertCountEqual(w_a.associated, [])
        self.assertCountEqual(w_b.associated, [])

    def test_stations(self):
        def test_station(station_name, expected_a, expected_b):
            station_a, station_b = self.tg.stations[station_name.upper()]
            self.assertEqual(station_a, self.tg.nodes[expected_a])
            self.assertEqual(station_b, self.tg.nodes[expected_b])

        test_station("u|1", "uA", "uB")
        test_station("v|1", "vA", "vB")
        test_station("uHat|1", "uHatA", "uHatB")
        test_station("vHat|1", "vHatA", "vHatB")


    def test_signals(self):
        def test_signal(signal_name, track):
            self.assertTrue(signal_name in [signal.id for signal in self.tg.signals])
            signals = [signal for signal in self.tg.signals if signal.id == signal_name]
            self.assertEqual(len(signals), 1, f"Found multiple signals with the same name: {signals}")
            self.assertEqual(signals[0].track, self.tg.nodes[track])

        test_signal("u|A", "uA")
        test_signal("u|B", "uB")
        test_signal("w|A", "wA")
        test_signal("su|B", "suB")
        test_signal("suHat|B", "suHatB")

    def test_opposites(self):
        def test_opposite(track_a, opposite):
            ta = self.tg.nodes[track_a]
            tb = self.tg.nodes[opposite]
            self.assertCountEqual(ta.outgoing[0].opposites, tb.outgoing)

        test_opposite("s1A", "s1B")
        test_opposite("s2A", "s2B")
        test_opposite("s3A", "s3B")
        test_opposite("s4A", "s4B")



class TestBlockGraph(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bg = graph_from_file("location_test.json")

    def test_general_block_graph(self):
        self.assertEqual(len(self.bg.nodes), 24, f"Should be 24 signals: {self.bg.nodes}")
        self.assertEqual(len(self.bg.edges), 26, f"Should be 26 routes: {self.bg.edges}")

        for e in self.bg.edges:
            self.assertEqual(e.length, 100, f"Length is not 100m for {e}")

    def test_block_node(self):
        u_a = self.bg.nodes["u|A"]
        self.assertEqual(len(u_a.outgoing), 1)
        self.assertEqual(len(u_a.incoming), 1)

        w_a = self.bg.nodes["w|A"]
        self.assertEqual(len(w_a.outgoing), 1)
        self.assertEqual(len(w_a.incoming), 2)

        s5_a = self.bg.nodes["s5|A"]
        self.assertEqual(len(s5_a.outgoing), 2)
        self.assertEqual(len(s5_a.incoming), 1)

    def test_track_graph_relation(self):
        def te(tn: str):
            return self.bg.tg.nodes[tn].outgoing[0]

        def test_track_route(block, track_nodes):
            node = self.bg.nodes[block]
            self.assertCountEqual(node.outgoing[0].track_route, [te(tn) for tn in track_nodes], f"Incorrect for signal {block}")

        test_track_route("u|A", ["suA", "wA"])
        test_track_route("w|A", ["s1A"])
        test_track_route("s1|A", ["s2A"])
        test_track_route("u|B", ["uA"])

    def test_track_graph_relation_diverging_switch(self):
        node = self.bg.nodes["s5|A"]
        self.assertEqual(len(node.outgoing), 2)

    # def test_block_relation(self):
    #     self.fail("Implement test")


    def test_path_finding(self):
        start_a, _ = self.bg.get_block_from_station("U|1")
        end_a, _ = self.bg.get_block_from_station("V|1")
        path = self.bg.calculate_path(start_a, end_a)
        #TODO: should this include the starting track, currently does not
        self.assertEqual(len(path), 8, f"Length of path should be 9: {path}")


class TestScenario(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bg = graph_from_file("location_test.json")
        cls.scenario = scenario_from_file("scenario_test.json", cls.bg)


class TestUnsafeIntervals(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        bg = graph_from_file("location_test.json")
        scenario = scenario_from_file("scenario_test.json", bg)
        scenario.process()
        cls.g = scenario.g

    def test_unsafe_intervals(self):

        def test_unsafe(left: IntervalStore, right: list[Tuple[float, float]]):
            self.assertCountEqual(left.unsafe_intervals, [Interval(s, e) for s, e in right])

        node = self.g.nodes["u|A"]
        for edge in node.outgoing:
            test_unsafe(edge, [(2, 3), (16, 17)])

        node = self.g.nodes["w|A"]
        test_unsafe(node, [(2, 3), (16, 17)])
        for edge in node.outgoing:
            test_unsafe(edge, [(3, 4), (15, 16)])

        node = self.g.nodes["s1|A"]
        test_unsafe(node, [(3, 4), (15, 16)])
        for edge in node.outgoing:
            test_unsafe(edge, [(4, 5), (14, 15)])

        node = self.g.nodes["s2|A"]
        test_unsafe(node, [(4, 5), (14, 15)])
        for edge in node.outgoing:
            test_unsafe(edge, [(5, 6), (13, 14)])

        node = self.g.nodes["s3|A"]
        test_unsafe(node, [(5, 6), (13, 14)])
        for edge in node.outgoing:
            test_unsafe(edge, [(6, 7), (12, 13)])

        node = self.g.nodes["s4|A"]
        test_unsafe(node, [(6, 7), (12, 13)])
        for edge in node.outgoing:
            test_unsafe(edge, [(7, 8), (11, 12)])

        node = self.g.nodes["s5|A"]
        test_unsafe(node, [(7, 8), (11, 12)])
        for edge in node.outgoing:
            test_unsafe(edge, [(8, 9), (10, 11)])


class TestSafeIntervals(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        bg = graph_from_file("location_test.json")
        scenario = scenario_from_file("scenario_test.json", bg)
        scenario.process()
        heuristic = {node.name: 0 for node in bg.nodes.values()}
        new_agent = copy(scenario.agents[0])
        new_agent.id = -1
        cls.fsipp = FSIPP(scenario.fsipp(new_agent), heuristic)


    def test_safe_intervals(self):
        node = self.fsipp.g.nodes["w|A"]
        self.assertCountEqual(node.safe_intervals, [Interval(a, b) for a,b in [(0, 2), (3, 16), (17, 36)]])
        node = self.fsipp.g.nodes["s2|A"]
        self.assertCountEqual(node.safe_intervals, [Interval(a, b) for a,b in [(0, 4), (5, 14), (15, 36)]])


if __name__ == '__main__':
    unittest.main()
