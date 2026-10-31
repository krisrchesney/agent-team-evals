import unittest

from patchkit import Hunk, Line
from patchkit.lines import join_lines, split_lines


class LinesTest(unittest.TestCase):
    def test_split_keeps_newlines(self):
        self.assertEqual(split_lines("a\nb\n"), ["a\n", "b\n"])
        self.assertEqual(split_lines("a\nb"), ["a\n", "b"])
        self.assertEqual(split_lines(""), [])

    def test_carriage_returns_stay_in_the_line(self):
        self.assertEqual(split_lines("a\r\nb\rc\n"), ["a\r\n", "b\rc\n"])
        self.assertEqual(join_lines(split_lines("a\r\nb")), "a\r\nb")


class ModelsTest(unittest.TestCase):
    def test_hunk_reversed(self):
        h = Hunk(3, 2, 3, 3, [Line(" ", "x\n"), Line("+", "y\n"), Line(" ", "z\n")])
        r = h.reversed()
        self.assertEqual((r.old_start, r.old_len, r.new_start, r.new_len), (3, 3, 3, 2))
        self.assertEqual([ln.tag for ln in r.lines], [" ", "-", " "])
