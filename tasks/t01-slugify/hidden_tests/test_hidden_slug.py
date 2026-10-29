import unittest

from textkit import slugify


class HiddenSlugify(unittest.TestCase):
    def test_backward_compatible(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_accents(self):
        self.assertEqual(slugify("Crème Brûlée"), "creme-brulee")
        self.assertEqual(slugify("Ångström Über"), "angstrom-uber")

    def test_non_ascii_dropped(self):
        self.assertEqual(slugify("tea 茶 time"), "tea-time")

    def test_collapse_separators(self):
        self.assertEqual(slugify("a  --  b__c!!d"), "a-b-c-d")

    def test_no_edge_dashes(self):
        self.assertEqual(slugify("  --Hello--  "), "hello")
        self.assertEqual(slugify("!Wow!"), "wow")

    def test_empty(self):
        self.assertEqual(slugify(""), "")
        self.assertEqual(slugify("!!! ???"), "")

    def test_digits_kept(self):
        self.assertEqual(slugify("Top 10 Games of 2026"), "top-10-games-of-2026")

    def test_max_length_word_boundary(self):
        self.assertEqual(slugify("the quick brown fox", max_length=12), "the-quick")
        self.assertEqual(slugify("the quick brown fox", max_length=9), "the-quick")

    def test_max_length_exact_and_none(self):
        self.assertEqual(slugify("the quick", max_length=100), "the-quick")
        self.assertEqual(slugify("the quick", max_length=None), "the-quick")

    def test_max_length_hard_cut_first_word(self):
        self.assertEqual(slugify("supercalifragilistic word", max_length=5), "super")

    def test_max_length_no_trailing_dash(self):
        out = slugify("ab cd ef", max_length=3)
        self.assertEqual(out, "ab")
        self.assertFalse(out.endswith("-"))


if __name__ == "__main__":
    unittest.main()
