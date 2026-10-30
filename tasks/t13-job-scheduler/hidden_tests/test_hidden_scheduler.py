"""Hidden grader for t13. Tests are named after the requirement they check. The methods marked
BUG isolate one planted bug each, so partial credit shows which bugs an agent found; the rest
pass on the starting code, except the scenario at the end (all requirements together)."""
import unittest

from jobkit import FakeClock, Scheduler


class RecordingClock(FakeClock):
    def __init__(self, start=0.0):
        super().__init__(start)
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        super().sleep(seconds)

    def tick(self, seconds):
        """Time passing inside a job body: moves now() but is not a sleep the scheduler made."""
        self._now += seconds


def make_fn(log, clock, name, duration=0, fail_times=0):
    """A job body that logs (name, attempt, start time), takes `duration`, and raises on its
    first `fail_times` attempts."""
    state = {"n": 0}

    def fn():
        state["n"] += 1
        log.append((name, state["n"], clock.now()))
        if duration:
            clock.tick(duration)
        if state["n"] <= fail_times:
            raise RuntimeError(f"{name} attempt {state['n']}")
        return f"{name}-ok"

    return fn


class HiddenScheduler(unittest.TestCase):
    def setUp(self):
        self.clock = RecordingClock()
        self.log = []

    def sched(self, **kw):
        return Scheduler(self.clock, **kw)

    def fn(self, name, **kw):
        return make_fn(self.log, self.clock, name, **kw)

    def names(self):
        return [entry[0] for entry in self.log]

    # ---- R1 submitting and checking ---------------------------------------------------------
    def test_R1_duplicate_id_and_bad_max_retries(self):
        s = self.sched()
        s.submit("a", self.fn("a"))
        with self.assertRaises(ValueError):
            s.submit("a", self.fn("a"))
        for bad in (-1, 1.5, "2", None):
            with self.subTest(max_retries=bad):
                with self.assertRaises(ValueError):
                    s.submit("b", self.fn("b"), max_retries=bad)

    def test_R1_unknown_dependency_raises_before_anything_runs(self):
        s = self.sched()
        s.submit("a", self.fn("a"))
        s.submit("b", self.fn("b"), deps=["nope"])
        with self.assertRaises(KeyError):
            s.run()
        self.assertEqual(self.log, [])

    def test_R1_cycle_raises_before_anything_runs(self):
        s = self.sched()
        s.submit("free", self.fn("free"))
        s.submit("a", self.fn("a"), deps=["c"])
        s.submit("b", self.fn("b"), deps=["a"])
        s.submit("c", self.fn("c"), deps=["b"])
        with self.assertRaises(ValueError):
            s.run()
        self.assertEqual(self.log, [])
        t = self.sched()
        t.submit("me", self.fn("me"), deps=["me"])
        with self.assertRaises(ValueError):
            t.run()

    def test_R1_dependencies_may_be_submitted_later(self):
        s = self.sched()
        s.submit("b", self.fn("b"), deps=["a"])
        s.submit("a", self.fn("a"))
        self.assertEqual(s.run(), {"b": "done", "a": "done"})
        self.assertEqual(self.names(), ["a", "b"])

    # ---- R2 order -----------------------------------------------------------------------------
    def test_R2_lowest_priority_number_first(self):
        s = self.sched()
        s.submit("p5", self.fn("p5"), priority=5)
        s.submit("p1", self.fn("p1"), priority=1)
        s.submit("p3", self.fn("p3"), priority=3)
        s.submit("p0", self.fn("p0"))
        s.run()
        self.assertEqual(self.names(), ["p0", "p1", "p3", "p5"])

    def test_R2_ties_run_in_submission_order(self):
        s = self.sched()
        for name in ("z", "a", "m", "b"):
            s.submit(name, self.fn(name), priority=2)
        s.run()
        self.assertEqual(self.names(), ["z", "a", "m", "b"])

    def test_R2_retried_job_keeps_its_place_BUG(self):
        # No retry delay, so x is ready again at once; it still sits ahead of y and z.
        s = self.sched(base_delay=0)
        s.submit("x", self.fn("x", fail_times=1), max_retries=1)
        s.submit("y", self.fn("y"))
        s.submit("z", self.fn("z"))
        s.run()
        self.assertEqual([(n, a) for n, a, _ in self.log],
                         [("x", 1), ("x", 2), ("y", 1), ("z", 1)])

    def test_R2_dependent_waits_even_with_better_priority(self):
        s = self.sched()
        s.submit("dep", self.fn("dep"), priority=9)
        s.submit("child", self.fn("child"), priority=0, deps=["dep"])
        s.submit("other", self.fn("other"), priority=5)
        s.run()
        self.assertEqual(self.names(), ["other", "dep", "child"])

    # ---- R3 attempts and delays ---------------------------------------------------------------------
    def test_R3_attempts_are_max_retries_plus_one_BUG(self):
        for retries in (0, 1, 2, 3):
            with self.subTest(max_retries=retries):
                self.setUp()
                s = self.sched(base_delay=0)
                s.submit("j", self.fn("j", fail_times=99), max_retries=retries)
                self.assertEqual(s.run(), {"j": "failed"})
                self.assertEqual(len(self.log), retries + 1)
                self.assertEqual(str(s.errors["j"]), f"j attempt {retries + 1}")

    def test_R3_retry_delay_counts_from_the_failure_BUG(self):
        # The first attempt takes 3 s and then fails at t=3; the retry is due at 3 + 2 = 5.
        s = self.sched(base_delay=2)
        s.submit("slow", self.fn("slow", duration=3, fail_times=1), max_retries=1)
        s.run()
        self.assertEqual([t for _, _, t in self.log], [0, 5])
        self.assertEqual(self.clock.sleeps, [2])

    def test_R3_delay_doubles_and_is_capped(self):
        s = self.sched(base_delay=1, max_delay=10)
        s.submit("j", self.fn("j", fail_times=5), max_retries=6)
        self.assertEqual(s.run(), {"j": "done"})
        # retries wait 1, 2, 4, 8, then min(10, 16) = 10
        self.assertEqual([t for _, _, t in self.log], [0, 1, 3, 7, 15, 25])

    def test_R3_cap_below_base(self):
        s = self.sched(base_delay=5, max_delay=3)
        s.submit("j", self.fn("j", fail_times=2), max_retries=3)
        s.run()
        self.assertEqual([t for _, _, t in self.log], [0, 3, 6])

    def test_R3_success_status_and_exceptions_only(self):
        s = self.sched()
        s.submit("a", lambda: 42)
        s.submit("b", lambda: [1, 2])
        self.assertEqual(s.run(), {"a": "done", "b": "done"})
        self.assertEqual(s.results, {"a": 42, "b": [1, 2]})

    # ---- R4 readiness and sleeping -----------------------------------------------------------------------
    def test_R4_waiting_job_does_not_hold_up_ready_jobs_BUG(self):
        s = self.sched(base_delay=5)
        s.submit("a", self.fn("a", fail_times=1), priority=0, max_retries=1)
        s.submit("b", self.fn("b"), priority=5)
        s.run()
        self.assertEqual(self.log, [("a", 1, 0), ("b", 1, 0), ("a", 2, 5)])
        self.assertEqual(self.clock.sleeps, [5])

    def test_R4_sleeps_exactly_the_time_to_the_earliest_retry(self):
        s = self.sched(base_delay=4)
        s.submit("b", self.fn("b", duration=1, fail_times=1), priority=0, max_retries=1)
        s.submit("a", self.fn("a", duration=1, fail_times=1), priority=1, max_retries=1)
        s.run()
        # b fails at t=1 (retry due 5); a runs t=1..2 and fails (retry due 6). At t=2 nothing is
        # ready, so one sleep of 3; b's retry then runs until t=6, when a's retry is due already.
        self.assertEqual(self.log, [("b", 1, 0), ("a", 1, 1), ("b", 2, 5), ("a", 2, 6)])
        self.assertEqual(self.clock.sleeps, [3])

    def test_R4_no_sleep_when_nothing_waits(self):
        s = self.sched()
        s.submit("a", self.fn("a"))
        s.submit("b", self.fn("b", duration=2), deps=["a"])
        s.run()
        self.assertEqual(self.clock.sleeps, [])

    # ---- R5 dependencies -------------------------------------------------------------------------------------
    def test_R5_failed_dependency_skips_direct_dependents(self):
        s = self.sched()
        s.submit("a", self.fn("a", fail_times=99))
        s.submit("b", self.fn("b"), deps=["a"])
        s.submit("c", self.fn("c"))
        self.assertEqual(s.run(), {"a": "failed", "b": "skipped", "c": "done"})
        self.assertEqual(self.names(), ["a", "c"])

    def test_R5_skipping_is_transitive_BUG(self):
        s = self.sched()
        s.submit("a", self.fn("a", fail_times=99))
        s.submit("b", self.fn("b"), deps=["a"])
        s.submit("c", self.fn("c"), deps=["b"])
        s.submit("d", self.fn("d"), deps=["c"])
        s.submit("x", self.fn("x"))
        s.submit("e", self.fn("e"), deps=["x", "c"])
        self.assertEqual(s.run(), {"a": "failed", "b": "skipped", "c": "skipped",
                                   "d": "skipped", "x": "done", "e": "skipped"})
        self.assertEqual(sorted(self.names()), ["a", "x"])

    def test_R5_dependency_that_recovers_counts_as_done_BUG(self):
        s = self.sched(base_delay=1)
        s.submit("a", self.fn("a", fail_times=1), max_retries=1)
        s.submit("b", self.fn("b"), deps=["a"])
        s.submit("c", self.fn("c"), deps=["b"])
        self.assertEqual(s.run(), {"a": "done", "b": "done", "c": "done"})
        self.assertEqual(self.log, [("a", 1, 0), ("a", 2, 1), ("b", 1, 1), ("c", 1, 1)])

    def test_R5_exhausted_retries_then_skip(self):
        s = self.sched(base_delay=1)
        s.submit("a", self.fn("a", fail_times=99), max_retries=2)
        s.submit("b", self.fn("b"), deps=["a"])
        self.assertEqual(s.run(), {"a": "failed", "b": "skipped"})
        self.assertEqual(self.names(), ["a"] * len(self.log))  # b never ran

    # ---- R6 results ----------------------------------------------------------------------------------------------
    def test_R6_results_and_errors(self):
        s = self.sched(base_delay=0)
        s.submit("ok", lambda: {"v": 1})
        s.submit("bad", self.fn("bad", fail_times=99), max_retries=2)
        s.submit("child", self.fn("child"), deps=["bad"])
        status = s.run()
        self.assertEqual(status, {"ok": "done", "bad": "failed", "child": "skipped"})
        self.assertEqual(s.results, {"ok": {"v": 1}})
        self.assertEqual(set(s.errors), {"bad"})
        self.assertIsInstance(s.errors["bad"], RuntimeError)
        self.assertEqual(str(s.errors["bad"]), f"bad attempt {len(self.log)}")

    # ---- everything together -----------------------------------------------------------------------------------------
    def test_R1_to_R6_scenario_all_features_together(self):
        s = self.sched(base_delay=2, max_delay=5)
        s.submit("fetch", self.fn("fetch", duration=1, fail_times=1), priority=0, max_retries=2)
        s.submit("parse", self.fn("parse", duration=1), priority=1, deps=["fetch"])
        s.submit("report", self.fn("report"), priority=2, deps=["parse"])
        s.submit("lint", self.fn("lint", duration=2), priority=1)
        s.submit("docs", self.fn("docs"), priority=3, deps=["lint"])
        s.submit("flaky", self.fn("flaky", fail_times=99), priority=0, max_retries=1)
        s.submit("after_flaky", self.fn("after_flaky"), priority=0, deps=["flaky"])
        s.submit("after_after", self.fn("after_after"), priority=0, deps=["after_flaky"])
        status = s.run()
        self.assertEqual(status, {
            "fetch": "done", "parse": "done", "report": "done", "lint": "done", "docs": "done",
            "flaky": "failed", "after_flaky": "skipped", "after_after": "skipped"})
        self.assertEqual(self.log, [
            ("fetch", 1, 0), ("flaky", 1, 1), ("lint", 1, 1), ("fetch", 2, 3),
            ("flaky", 2, 4), ("parse", 1, 4), ("report", 1, 5), ("docs", 1, 5)])
        self.assertEqual(self.clock.now(), 5)
        self.assertEqual(str(s.errors["flaky"]), "flaky attempt 2")


if __name__ == "__main__":
    unittest.main()
