import unittest

from breakerkit import CircuitBreaker


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class TestBreaker(unittest.TestCase):
    def test_opens_after_threshold(self):
        clock = Clock()
        b = CircuitBreaker(2, 100, 10, clock=clock)
        b.record_failure()
        self.assertTrue(b.allow())
        b.record_failure()
        self.assertFalse(b.allow())
        self.assertEqual(b.state, "open")

    def test_closes_again_after_cooldown(self):
        clock = Clock()
        b = CircuitBreaker(1, 100, 10, clock=clock)
        b.record_failure()
        clock.t += 11
        self.assertTrue(b.allow())


if __name__ == "__main__":
    unittest.main()
