import unittest

from jobkit import FakeClock, Scheduler


class TestScheduler(unittest.TestCase):
    def test_runs_in_priority_order(self):
        order = []
        s = Scheduler(FakeClock())
        s.submit("low", lambda: order.append("low"), priority=5)
        s.submit("high", lambda: order.append("high"), priority=1)
        self.assertEqual(s.run(), {"low": "done", "high": "done"})
        self.assertEqual(order, ["high", "low"])

    def test_dependency_runs_first(self):
        order = []
        s = Scheduler(FakeClock())
        s.submit("b", lambda: order.append("b"), deps=["a"])
        s.submit("a", lambda: order.append("a"))
        s.run()
        self.assertEqual(order, ["a", "b"])

    def test_duplicate_id(self):
        s = Scheduler(FakeClock())
        s.submit("a", lambda: 1)
        with self.assertRaises(ValueError):
            s.submit("a", lambda: 2)


if __name__ == "__main__":
    unittest.main()
