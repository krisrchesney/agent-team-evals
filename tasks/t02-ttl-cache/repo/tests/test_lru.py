import unittest

from cachekit import LRUCache


class TestLRU(unittest.TestCase):
    def test_evicts_least_recent(self):
        c = LRUCache(2)
        c.set("a", 1)
        c.set("b", 2)
        c.get("a")
        c.set("c", 3)
        self.assertIn("a", c)
        self.assertNotIn("b", c)

    def test_capacity_validation(self):
        with self.assertRaises(ValueError):
            LRUCache(0)


if __name__ == "__main__":
    unittest.main()
