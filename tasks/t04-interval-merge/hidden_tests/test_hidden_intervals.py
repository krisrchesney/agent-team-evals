"""Hidden grader for t04. Each test_bug_* method isolates one planted bug, so partial credit
shows which bugs an agent found. The other tests pass on the starting code, except the random
check at the end, which exercises every requirement at once."""
import copy
import random
import unittest

from calkit import free_slots, merge


def covered(intervals):
    """Brute force: the integer points t with start <= t < end for some interval."""
    return {t for s, e in intervals for t in range(s, e)}


class HiddenIntervals(unittest.TestCase):
    # Behaviour the starting code already gets right (req 2, 3, 5, 6).

    def test_backward_compatible(self):
        self.assertEqual(merge([[1, 3], [2, 4], [6, 8]]), [[1, 4], [6, 8]])
        self.assertEqual(free_slots([[1, 2], [4, 10]], 0, 10), [[0, 1], [2, 4]])

    def test_merge_empty_and_single(self):
        self.assertEqual(merge([]), [])
        self.assertEqual(merge([[2, 5]]), [[2, 5]])

    def test_gap_stays_separate(self):
        self.assertEqual(merge([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_free_slots_clips_and_ignores_outside(self):
        busy = [[-5, 1], [3, 4], [8, 12], [15, 20]]
        self.assertEqual(free_slots(busy, 0, 10), [[1, 3], [4, 8]])

    # One planted bug per method.

    def test_bug_touching_intervals_merge(self):
        # Req 3: [1, 3) and [3, 5) touch, so they form one block.
        self.assertEqual(merge([[1, 3], [3, 5]]), [[1, 5]])
        self.assertEqual(merge([[0, 2], [2, 4], [4, 6], [8, 9]]), [[0, 6], [8, 9]])

    def test_bug_unsorted_input(self):
        # Req 2: input order must not matter; output is sorted by start.
        self.assertEqual(merge([[5, 7], [1, 2]]), [[1, 2], [5, 7]])
        self.assertEqual(merge([[6, 8], [1, 4], [2, 5]]), [[1, 5], [6, 8]])

    def test_bug_contained_interval_keeps_outer_end(self):
        # Req 2: an interval inside another must not shrink the block.
        self.assertEqual(merge([[1, 10], [2, 3]]), [[1, 10]])
        self.assertEqual(merge([[0, 8], [1, 2], [5, 6]]), [[0, 8]])

    def test_bug_input_not_modified(self):
        # Req 4: neither the list nor the pairs inside it change.
        data = [[1, 3], [2, 5], [7, 9]]
        before = copy.deepcopy(data)
        self.assertEqual(merge(data), [[1, 5], [7, 9]])
        self.assertEqual(data, before)

    def test_bug_free_slots_trailing_gap(self):
        # Req 5 and 6: the time after the last busy block, up to window_end, is free.
        self.assertEqual(free_slots([[2, 3]], 0, 10), [[0, 2], [3, 10]])
        self.assertEqual(free_slots([[0, 4]], 0, 10), [[4, 10]])
        self.assertEqual(free_slots([], 0, 10), [[0, 10]])

    # Every requirement at once, against a brute-force model (seeded, deterministic).

    def test_random_against_brute_force(self):
        rng = random.Random(4)
        for _ in range(300):
            data = []
            for _ in range(rng.randint(0, 8)):
                s = rng.randint(0, 30)
                data.append([s, s + rng.randint(1, 6)])
            before = copy.deepcopy(data)
            out = merge(data)
            self.assertEqual(data, before)
            self.assertEqual(covered(out), covered(data))
            for a, b in zip(out, out[1:]):
                self.assertLess(a[1], b[0])  # sorted, with a real gap between blocks
            ws, we = rng.randint(0, 15), rng.randint(16, 40)
            gaps = free_slots(data, ws, we)
            self.assertEqual(covered(gaps), set(range(ws, we)) - covered(data))
            for a, b in zip(gaps, gaps[1:]):
                self.assertLess(a[1], b[0])
            self.assertTrue(all(s < e for s, e in gaps))


if __name__ == "__main__":
    unittest.main()
