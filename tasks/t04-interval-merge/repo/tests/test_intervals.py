import unittest

from calkit import free_slots, merge


class TestIntervals(unittest.TestCase):
    def test_merge_overlapping(self):
        self.assertEqual(merge([[1, 3], [2, 4], [6, 8]]), [[1, 4], [6, 8]])

    def test_free_slots_between_meetings(self):
        self.assertEqual(free_slots([[1, 2], [4, 10]], 0, 10), [[0, 1], [2, 4]])


if __name__ == "__main__":
    unittest.main()
