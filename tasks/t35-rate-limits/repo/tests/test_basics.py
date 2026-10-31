import unittest

from ratelimit import Decision, FixedClock, MemoryStore


class DecisionTest(unittest.TestCase):
    def test_headers_allowed(self):
        d = Decision(True, 10, 7, 0.0, 2.2)
        self.assertEqual(d.headers(), {"X-RateLimit-Limit": "10", "X-RateLimit-Remaining": "7", "X-RateLimit-Reset": "3"})

    def test_headers_denied_has_retry_after(self):
        d = Decision(False, 10, 0, 0.2, 5.0)
        self.assertEqual(d.headers()["Retry-After"], "1")

    def test_headers_never_retry(self):
        self.assertNotIn("Retry-After", Decision(False, 10, 0, None, 5.0).headers())


class StoreTest(unittest.TestCase):
    def test_store_copies(self):
        s = MemoryStore()
        state = {"hits": [1.0]}
        s.set("r", "k", state)
        state["hits"].append(2.0)
        got = s.get("r", "k")
        self.assertEqual(got, {"hits": [1.0]})
        got["hits"].append(9.0)
        self.assertEqual(s.get("r", "k"), {"hits": [1.0]})

    def test_keys_and_delete(self):
        s = MemoryStore()
        s.set("r", "b", {})
        s.set("r", "a", {})
        self.assertEqual(s.keys("r"), ["a", "b"])
        s.delete("r", "a")
        self.assertEqual(s.keys("r"), ["b"])


class ClockTest(unittest.TestCase):
    def test_fixed_clock(self):
        c = FixedClock()
        c.advance(2.5)
        self.assertEqual(c.now(), 1002.5)
