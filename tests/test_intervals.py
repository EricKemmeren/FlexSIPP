import unittest

from flexsipp.util.intervals import Interval


class TestInterval(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(Interval(1, 2))
        self.assertTrue(Interval(1, 1))
        self.assertFalse(Interval(2, 1))

    def test_union(self):
        self.assertEqual(Interval(1, 2) | Interval(2, 3), Interval(1, 3))
        self.assertEqual(Interval(1, 2) | Interval(0, 3), Interval(0, 3))
        with self.assertRaises(ValueError):
            Interval(1, 2) | Interval(5, 10)

    def test_intersection(self):
        self.assertTrue(Interval(1, 2) & Interval(2, 3))
        self.assertTrue(Interval(1, 2) & Interval(0, 3))
        self.assertFalse(Interval(1, 2) & Interval(3, 4))

    def test_merge(self):
        a = Interval(1, 2)
        a.merge(Interval(2, 3))
        self.assertEqual(a, Interval(1, 3))
        a = Interval(1, 2)
        a.merge(Interval(0, 3))
        self.assertEqual(a, Interval(0, 3))
        a = Interval(1, 2)
        a.merge(Interval(5, 10))
        self.assertEqual(a, Interval(1, 10))

if __name__ == '__main__':
    unittest.main()
