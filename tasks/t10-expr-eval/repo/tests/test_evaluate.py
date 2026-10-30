import unittest

from exprkit import evaluate


class TestEvaluate(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(evaluate("1 + 2 * 3"), 7)
        self.assertEqual(evaluate("(1 + 2) * 3"), 9)

    def test_subtraction_is_left_associative(self):
        self.assertEqual(evaluate("10 - 4 - 3"), 3)


if __name__ == "__main__":
    unittest.main()
