import unittest

from cachekit import LRUCache


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class HiddenTTL(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()

    def make(self, capacity=3, ttl=None):
        return LRUCache(capacity, ttl=ttl, clock=self.clock)

    def test_no_ttl_unchanged(self):
        c = LRUCache(2)
        c.set("a", 1)
        c.set("b", 2)
        c.get("a")
        c.set("c", 3)
        self.assertEqual(c.get("a"), 1)
        self.assertIsNone(c.get("b"))
        self.assertEqual(len(c), 2)

    def test_capacity_validation(self):
        with self.assertRaises(ValueError):
            LRUCache(0, ttl=5)

    def test_expires_at_boundary(self):
        c = self.make(ttl=10)
        c.set("a", 1)
        self.clock.t += 9.5
        self.assertEqual(c.get("a"), 1)
        self.clock.t += 0.5
        self.assertIsNone(c.get("a"))
        self.assertEqual(c.get("a", "dflt"), "dflt")

    def test_contains_and_len_ignore_expired(self):
        c = self.make(ttl=5)
        c.set("a", 1)
        c.set("b", 2, ttl=100)
        self.clock.t += 6
        self.assertNotIn("a", c)
        self.assertIn("b", c)
        self.assertEqual(len(c), 1)

    def test_per_entry_ttl_override(self):
        c = self.make(ttl=100)
        c.set("short", 1, ttl=1)
        c.set("forever", 2, ttl=None)
        self.clock.t += 1_000_000
        self.assertIsNone(c.get("short"))
        self.assertEqual(c.get("forever"), 2)

    def test_reset_timer_on_set(self):
        c = self.make(ttl=10)
        c.set("a", 1)
        self.clock.t += 8
        c.set("a", 2)
        self.clock.t += 8
        self.assertEqual(c.get("a"), 2)

    def test_get_does_not_extend(self):
        c = self.make(ttl=10)
        c.set("a", 1)
        self.clock.t += 6
        self.assertEqual(c.get("a"), 1)
        self.clock.t += 6
        self.assertIsNone(c.get("a"))

    def test_evict_expired_before_lru(self):
        c = self.make(capacity=2)
        c.set("old_live", 1)  # never expires, least recently used
        c.set("dying", 2, ttl=1)
        self.clock.t += 2
        c.set("new", 3)
        self.assertEqual(c.get("old_live"), 1)
        self.assertEqual(c.get("new"), 3)
        self.assertEqual(len(c), 2)

    def test_lru_eviction_still_works_with_ttl(self):
        c = self.make(capacity=2, ttl=100)
        c.set("a", 1)
        c.set("b", 2)
        c.get("a")
        c.set("c", 3)
        self.assertNotIn("b", c)
        self.assertIn("a", c)

    def test_purge_expired(self):
        c = self.make(capacity=5, ttl=5)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3, ttl=None)
        self.clock.t += 5
        self.assertEqual(c.purge_expired(), 2)
        self.assertEqual(c.purge_expired(), 0)
        self.assertEqual(len(c), 1)


if __name__ == "__main__":
    unittest.main()
