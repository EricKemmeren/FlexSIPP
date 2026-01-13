import unittest

from generation.generate import graph_from_file, scenario_from_file


class TestTrackGraph(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bg = graph_from_file("location_test.json")

    def test_general_track_graph(self):
        tg = self.bg.tg
        self.assertEqual(len(tg.nodes), 32, "In total 32 nodes")
        self.assertEqual(len(tg.edges), 34, "In total 34 edges")
        self.assertEqual(len(tg.signals), 24, "In total 24 signals")

    def test_track_node(self):
        tg = self.bg.tg
        s1A = tg.nodes["s1A"]
        self.assertCountEqual(s1A.associated, [])
        self.assertCountEqual(s1A.opposites,  [tg.nodes["s1B"]])
        self.assertEqual(len(s1A.incoming), 1)
        self.assertEqual(len(s1A.outgoing), 1)

    def test_track_edge(self):
        tg = self.bg.tg
        self.assertEqual(tg.nodes["uA"].outgoing[0].length,  100)
        self.assertEqual(tg.nodes["suA"].outgoing[0].length, 0)
        self.assertEqual(tg.nodes["swA"].outgoing[0].length, 100)
        self.assertEqual(tg.nodes["uB"].outgoing[0].length,  100)
        self.assertEqual(tg.nodes["suB"].outgoing[0].length, 0)
        self.assertEqual(tg.nodes["swB"].outgoing[0].length, 100)

    def test_bumper_node(self):
        tg = self.bg.tg
        uA = tg.nodes["uA"]
        self.assertEqual(uA.direction, "A")
        self.assertCountEqual(uA.opposites, [tg.nodes["uB"]])
        self.assertCountEqual(uA.associated, [])
        self.assertEqual(len(uA.outgoing), 1)
        self.assertEqual(len(uA.incoming), 1)

    def test_switch_node(self):
        tg = self.bg.tg
        wA  = tg.nodes["wA"]
        wBL = tg.nodes["wBL"]
        wBR = tg.nodes["wBR"]
        self.assertEqual(len(wA.outgoing), 1)
        self.assertEqual(len(wA.incoming), 2)

        self.assertCountEqual(wA.opposites, [wBL, wBR])
        self.assertCountEqual(wBL.opposites, [wA])
        self.assertCountEqual(wBR.opposites, [wA])

        self.assertCountEqual(wA.associated, [])
        self.assertCountEqual(wBL.associated, [wBR])
        self.assertCountEqual(wBR.associated, [wBL])

class TestBlockGraph(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bg = graph_from_file("location_test.json")
        cls.scenario = scenario_from_file("scenario_test.json", cls.bg)

    def test_general_block_graph(self):
        self.assertEqual(len(self.bg.nodes), 24, "Should be 24 signals")
        self.assertEqual(len(self.bg.edges), 26, "Should be 26 routes")

    def test_path_finding(self):
        startA, startB = self.bg.get_block_from_station("U|1")
        endA, endB = self.bg.get_block_from_station("V|1")
        path = self.bg.calculate_path(startA, endA)
        self.assertEqual(len(path), 8, "Length of path should be 8")

    def test_create_scenario(self):
        self.scenario.process()
        print(self.scenario)


if __name__ == '__main__':
    unittest.main()
