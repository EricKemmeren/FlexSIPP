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
        self.assertEqual(tg.nodes["wA"].outgoing[0].length, 100)
        self.assertEqual(tg.nodes["uB"].outgoing[0].length,  100)
        self.assertEqual(tg.nodes["suB"].outgoing[0].length, 0)
        self.assertEqual(tg.nodes["wBR"].outgoing[0].length, 100)
        self.assertEqual(tg.nodes["wBL"].outgoing[0].length, 100)

    def test_bumper_node(self):
        tg = self.bg.tg
        uA = tg.nodes["uA"]
        self.assertEqual(uA.direction, "A")
        self.assertCountEqual(uA.opposites, [tg.nodes["uB"]])
        self.assertCountEqual(uA.associated, [tg.nodes["uB"]]) # TODO: is this wanted?
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
        bg = self.bg
        self.assertEqual(len(bg.nodes), 24, "Should be 24 signals")
        self.assertEqual(len(bg.edges), 26, "Should be 26 routes")

        for e in bg.edges:
            self.assertEqual(e.length, 100, f"Length is not 100m for {e}")

    def test_block_node(self):
        bg = self.bg
        uA = bg.nodes["u|A"]
        self.assertEqual(len(uA.outgoing), 1)
        self.assertEqual(len(uA.incoming), 1)

        wA = bg.nodes["w|A"]
        self.assertEqual(len(wA.outgoing), 1)
        self.assertEqual(len(wA.incoming), 2)

        s5A = bg.nodes["s5|A"]
        self.assertEqual(len(s5A.outgoing), 2)
        self.assertEqual(len(s5A.incoming), 1)

    def test_track_graph_relation(self):
        bg = self.bg
        def te(tn: str):
            return bg.tg.nodes[tn].outgoing[0]

        def test_track_route(block, track_nodes):
            node = bg.nodes[block]
            self.assertCountEqual(node.outgoing[0].track_route, [te(tn) for tn in track_nodes], f"Incorrect for signal {block}")

        test_track_route("u|A", ["suA", "wA"])
        test_track_route("w|A", ["s1A"])
        test_track_route("s1|A", ["s2A"])



    def test_path_finding(self):
        bg = self.bg
        startA, startB = bg.get_block_from_station("U|1")
        endA, endB = bg.get_block_from_station("V|1")
        path = bg.calculate_path(startA, endA)
        self.assertEqual(len(path), 8, "Length of path should be 8")

    def test_create_scenario(self):
        self.scenario.process()
        print(self.scenario)


if __name__ == '__main__':
    unittest.main()
