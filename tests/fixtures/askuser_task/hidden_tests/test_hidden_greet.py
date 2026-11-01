import unittest

from pkg import greet


class Hidden(unittest.TestCase):
    def test_greet(self):
        self.assertEqual(greet("Ann"), "Hello, Ann!")
