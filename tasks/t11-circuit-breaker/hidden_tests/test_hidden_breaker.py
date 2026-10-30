"""Hidden grader for t11. Test names start with the requirement (R1..R9) they check."""
import random
import unittest

from breakerkit import CircuitBreaker, CircuitOpenError

T0 = 1000.0


class FakeClock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t


class HiddenBreaker(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()

    def make(self, threshold=3, window=10, cooldown=30, **kw):
        return CircuitBreaker(threshold, window, cooldown, clock=self.clock, **kw)

    def trip(self, b):
        for _ in range(b.failure_threshold):
            b.record_failure()

    def half_open(self, **kw):
        """A breaker opened at T0 and now (T0 + cooldown) half-open."""
        b = self.make(**kw)
        self.trip(b)
        self.clock.t = T0 + b.cooldown
        self.assertEqual(b.state, "half_open")
        return b

    # R1

    def test_r1_initial_state(self):
        b = self.make()
        self.assertEqual(b.state, "closed")
        self.assertEqual(b.transitions, [])
        self.assertTrue(b.allow())

    def test_r1_validation(self):
        bad = [
            dict(failure_threshold=0), dict(failure_threshold=-1), dict(failure_threshold=1.5),
            dict(window=0), dict(window=-1), dict(cooldown=0), dict(cooldown=-5),
            dict(half_open_successes=0), dict(half_open_successes=1.5),
            dict(half_open_successes=2, probe_limit=1), dict(probe_limit=0),
        ]
        for over in bad:
            args = dict(failure_threshold=3, window=10, cooldown=30)
            args.update(over)
            with self.subTest(over=over):
                with self.assertRaises(ValueError):
                    CircuitBreaker(**args, clock=self.clock)

    def test_r1_valid_edge_values(self):
        CircuitBreaker(1, 0.001, 0.001, half_open_successes=2, probe_limit=2, clock=self.clock)
        CircuitBreaker(5, 10, 30, half_open_successes=3, probe_limit=10, clock=self.clock)

    # R2

    def test_r2_opens_on_the_threshold_failure(self):
        b = self.make()
        b.record_failure()
        b.record_failure()
        self.assertEqual(b.state, "closed")
        self.assertTrue(b.allow())
        self.clock.t += 1
        b.record_failure()
        self.assertEqual(b.state, "open")
        self.assertFalse(b.allow())
        self.assertEqual(b.transitions, [(T0 + 1, "closed", "open")])

    def test_r2_threshold_one(self):
        b = self.make(threshold=1)
        b.record_failure()
        self.assertEqual(b.state, "open")

    def test_r2_failure_exactly_window_old_does_not_count(self):
        b = self.make()
        b.record_failure()  # t = 0
        self.clock.t = T0 + 4
        b.record_failure()
        self.clock.t = T0 + 10  # the first failure is exactly 10 old
        b.record_failure()
        self.assertEqual(b.state, "closed")
        b.record_failure()  # now 4, 10 and 10 count
        self.assertEqual(b.state, "open")

    def test_r2_failure_just_inside_window_counts(self):
        b = self.make()
        b.record_failure()
        self.clock.t = T0 + 4
        b.record_failure()
        self.clock.t = T0 + 9.999
        b.record_failure()
        self.assertEqual(b.state, "open")

    def test_r2_old_failures_are_forgotten(self):
        b = self.make()
        b.record_failure()
        b.record_failure()
        self.clock.t = T0 + 500
        b.record_failure()
        b.record_failure()
        self.assertEqual(b.state, "closed")
        b.record_failure()
        self.assertEqual(b.state, "open")

    def test_r2_success_forgets_failures(self):
        b = self.make()
        b.record_failure()
        b.record_failure()
        b.record_success()
        b.record_failure()
        b.record_failure()
        self.assertEqual(b.state, "closed")
        b.record_failure()
        self.assertEqual(b.state, "open")

    def test_r2_allow_in_closed_is_free(self):
        b = self.make()
        self.assertTrue(all(b.allow() for _ in range(50)))
        self.assertEqual(b.state, "closed")

    # R3

    def test_r3_open_rejects(self):
        b = self.make()
        self.trip(b)
        self.clock.t = T0 + 29.999
        self.assertEqual(b.state, "open")
        self.assertFalse(b.allow())

    def test_r3_half_open_exactly_at_cooldown(self):
        b = self.make()
        self.trip(b)
        self.clock.t = T0 + 30
        self.assertEqual(b.state, "half_open")

    def test_r3_state_follows_the_clock_without_other_calls(self):
        b = self.make()
        self.trip(b)
        self.clock.t = T0 + 31
        self.assertEqual(b.state, "half_open")
        self.clock.t = T0 + 1000
        self.assertEqual(b.state, "half_open")

    def test_r3_results_while_open_are_ignored(self):
        b = self.make()
        self.trip(b)
        self.clock.t = T0 + 10
        b.record_failure()
        b.record_success()
        self.assertEqual(b.state, "open")
        self.assertEqual(b.retry_after(), 20.0)  # the cooldown was not restarted
        self.clock.t = T0 + 30
        self.assertEqual(b.state, "half_open")
        self.assertEqual(b.transitions, [(T0, "closed", "open"), (T0 + 30, "open", "half_open")])

    def test_r3_late_failure_after_cooldown_counts_as_half_open(self):
        b = self.make()
        self.trip(b)
        self.clock.t = T0 + 40
        b.record_failure()  # nobody asked for the state first
        self.assertEqual(b.state, "open")
        self.assertEqual(b.retry_after(), 30.0)
        self.assertEqual(b.transitions, [(T0, "closed", "open"), (T0 + 30, "open", "half_open"),
                                         (T0 + 40, "half_open", "open")])

    def test_r3_late_success_after_cooldown_counts_as_half_open(self):
        b = self.make()
        self.trip(b)
        self.clock.t = T0 + 40
        b.record_success()
        self.assertEqual(b.state, "closed")
        self.assertEqual(b.transitions, [(T0, "closed", "open"), (T0 + 30, "open", "half_open"),
                                         (T0 + 40, "half_open", "closed")])

    # R4

    def test_r4_default_is_one_probe(self):
        b = self.half_open()
        self.assertTrue(b.allow())
        self.assertFalse(b.allow())
        self.assertFalse(b.allow())

    def test_r4_probe_limit(self):
        b = self.half_open(probe_limit=3)
        self.assertEqual([b.allow() for _ in range(5)], [True, True, True, False, False])

    def test_r4_allow_while_open_uses_no_probe(self):
        b = self.make()
        self.trip(b)
        for _ in range(5):
            self.assertFalse(b.allow())
        self.clock.t = T0 + 30
        self.assertTrue(b.allow())
        self.assertFalse(b.allow())

    def test_r4_probes_are_fresh_each_half_open_period(self):
        b = self.half_open()
        self.assertTrue(b.allow())
        b.record_failure()
        self.assertEqual(b.state, "open")
        self.clock.t += 30
        self.assertEqual(b.state, "half_open")
        self.assertTrue(b.allow())
        self.assertFalse(b.allow())

    def test_r4_probes_used_do_not_leak_into_closed(self):
        b = self.half_open()
        self.assertTrue(b.allow())
        b.record_success()
        self.assertEqual(b.state, "closed")
        self.assertTrue(b.allow())
        self.assertTrue(b.allow())

    # R5

    def test_r5_failure_reopens_with_fresh_cooldown(self):
        b = self.half_open()
        self.clock.t += 5
        b.record_failure()
        self.assertEqual(b.state, "open")
        self.assertEqual(b.retry_after(), 30.0)
        self.clock.t += 29
        self.assertEqual(b.state, "open")
        self.clock.t += 1
        self.assertEqual(b.state, "half_open")

    def test_r5_needs_the_configured_number_of_successes(self):
        b = self.half_open(half_open_successes=3, probe_limit=3)
        for _ in range(3):
            self.assertTrue(b.allow())
        b.record_success()
        b.record_success()
        self.assertEqual(b.state, "half_open")
        b.record_success()
        self.assertEqual(b.state, "closed")

    def test_r5_success_count_restarts_on_each_half_open_period(self):
        b = self.half_open(half_open_successes=2, probe_limit=2)
        b.record_success()
        b.record_failure()
        self.assertEqual(b.state, "open")
        self.clock.t += 30
        self.assertEqual(b.state, "half_open")
        b.record_success()
        self.assertEqual(b.state, "half_open")
        b.record_success()
        self.assertEqual(b.state, "closed")

    def test_r5_closing_forgets_failures(self):
        b = self.make(window=1000)
        self.trip(b)
        self.clock.t += 30
        b.record_success()
        self.assertEqual(b.state, "closed")
        b.record_failure()
        b.record_failure()
        self.assertEqual(b.state, "closed")
        b.record_failure()
        self.assertEqual(b.state, "open")

    def test_r5_opening_forgets_old_failures(self):
        b = self.make(window=1000)
        b.record_failure()
        b.record_failure()
        b.record_failure()  # opens; all three are still inside the window
        self.clock.t += 30
        b.record_failure()  # half-open failure: opens again
        self.clock.t += 30
        b.record_success()  # half-open success: closes
        b.record_failure()
        b.record_failure()
        self.assertEqual(b.state, "closed")

    def test_r5_success_in_half_open_without_probe_still_counts(self):
        b = self.half_open()
        b.record_success()
        self.assertEqual(b.state, "closed")

    # R6

    def test_r6_full_lifecycle_log(self):
        b = self.make()
        self.trip(b)
        self.clock.t = T0 + 30
        b.allow()
        self.clock.t = T0 + 32
        b.record_failure()
        self.clock.t = T0 + 70
        b.record_success()
        self.assertEqual(b.transitions, [
            (T0, "closed", "open"),
            (T0 + 30, "open", "half_open"),
            (T0 + 32, "half_open", "open"),
            (T0 + 62, "open", "half_open"),
            (T0 + 70, "half_open", "closed"),
        ])

    def test_r6_half_open_time_when_observed_late(self):
        b = self.make()
        self.clock.t = T0 + 3
        self.trip(b)
        self.clock.t = T0 + 500
        self.assertEqual(b.transitions, [(T0 + 3, "closed", "open"), (T0 + 33, "open", "half_open")])

    def test_r6_each_move_listed_once(self):
        b = self.make()
        self.trip(b)
        self.clock.t = T0 + 31
        for _ in range(4):
            b.state
            b.allow()
            b.retry_after()
            b.transitions
        self.assertEqual(len(b.transitions), 2)

    def test_r6_returns_a_copy(self):
        b = self.make()
        self.trip(b)
        b.transitions.append("junk")
        b.transitions.clear()
        self.assertEqual(b.transitions, [(T0, "closed", "open")])

    # R7

    def test_r7_retry_after(self):
        b = self.make()
        self.assertEqual(b.retry_after(), 0.0)
        self.trip(b)
        self.assertEqual(b.retry_after(), 30.0)
        self.clock.t = T0 + 12.5
        self.assertEqual(b.retry_after(), 17.5)
        self.clock.t = T0 + 30
        self.assertEqual(b.retry_after(), 0.0)
        self.clock.t = T0 + 100
        self.assertEqual(b.retry_after(), 0.0)
        self.assertIsInstance(b.retry_after(), float)

    def test_r7_retry_after_after_close(self):
        b = self.half_open()
        b.record_success()
        self.assertEqual(b.retry_after(), 0.0)

    # R8

    def test_r8_reset_from_open(self):
        b = self.make()
        self.trip(b)
        self.clock.t = T0 + 5
        b.reset()
        self.assertEqual(b.state, "closed")
        self.assertEqual(b.transitions, [(T0, "closed", "open"), (T0 + 5, "open", "closed")])
        self.assertTrue(b.allow())
        b.record_failure()
        b.record_failure()
        self.assertEqual(b.state, "closed")

    def test_r8_reset_when_closed_forgets_failures_without_transition(self):
        b = self.make()
        b.record_failure()
        b.record_failure()
        b.reset()
        b.record_failure()
        b.record_failure()
        self.assertEqual(b.state, "closed")
        self.assertEqual(b.transitions, [])

    def test_r8_reset_from_half_open(self):
        b = self.half_open()
        b.allow()
        self.clock.t += 1
        b.reset()
        self.assertEqual(b.state, "closed")
        self.assertEqual(b.transitions[-1], (T0 + 31, "half_open", "closed"))

    def test_r8_reset_after_unobserved_cooldown(self):
        b = self.make()
        self.trip(b)
        self.clock.t = T0 + 100
        b.reset()
        self.assertEqual(b.transitions, [(T0, "closed", "open"), (T0 + 30, "open", "half_open"),
                                         (T0 + 100, "half_open", "closed")])

    # R9

    def test_r9_call_returns_result(self):
        b = self.make()
        self.assertEqual(b.call(lambda a, b=0: a + b, 2, b=5), 7)
        self.assertEqual(b.state, "closed")

    def test_r9_call_success_forgets_failures(self):
        b = self.make()
        b.record_failure()
        b.record_failure()
        b.call(lambda: None)
        b.record_failure()
        b.record_failure()
        self.assertEqual(b.state, "closed")

    def test_r9_failures_are_recorded_and_reraised(self):
        b = self.make()

        def boom():
            raise ValueError("x")

        for _ in range(3):
            with self.assertRaises(ValueError):
                b.call(boom)
        self.assertEqual(b.state, "open")

    def test_r9_open_breaker_does_not_call(self):
        b = self.make()
        self.trip(b)
        calls = []
        with self.assertRaises(CircuitOpenError):
            b.call(lambda: calls.append(1))
        self.assertEqual(calls, [])

    def test_r9_half_open_probe_success_closes(self):
        b = self.half_open()
        self.assertEqual(b.call(lambda: "ok"), "ok")
        self.assertEqual(b.state, "closed")

    def test_r9_half_open_probe_failure_reopens(self):
        b = self.half_open()
        with self.assertRaises(KeyError):
            b.call(lambda: {}["x"])
        self.assertEqual(b.state, "open")

    def test_r9_half_open_limits_concurrent_calls(self):
        b = self.half_open()
        seen = []

        def probe():
            seen.append("probe")
            with self.assertRaises(CircuitOpenError):
                b.call(lambda: seen.append("second"))  # a second call while the probe is running
            return "done"

        self.assertEqual(b.call(probe), "done")
        self.assertEqual(seen, ["probe"])

    def test_r9_unexpected_exception_is_not_counted(self):
        b = self.make(threshold=2, expected=(ValueError,))
        for _ in range(5):
            with self.assertRaises(KeyError):
                b.call(lambda: {}["x"])
        self.assertEqual(b.state, "closed")
        with self.assertRaises(ValueError):
            b.call(lambda: int("x"))
        self.assertEqual(b.state, "closed")
        with self.assertRaises(ValueError):
            b.call(lambda: int("x"))
        self.assertEqual(b.state, "open")

    def test_r9_unexpected_exception_is_not_a_success(self):
        b = self.make(expected=(ValueError,))
        b.record_failure()
        b.record_failure()
        with self.assertRaises(KeyError):
            b.call(lambda: {}["x"])
        with self.assertRaises(ValueError):
            b.call(lambda: int("x"))
        self.assertEqual(b.state, "open")

    def test_r9_unexpected_exception_gives_the_probe_back(self):
        b = self.half_open(expected=(ValueError,))
        with self.assertRaises(KeyError):
            b.call(lambda: {}["x"])
        self.assertEqual(b.state, "half_open")
        self.assertTrue(b.allow())
        self.assertFalse(b.allow())

    def test_r9_unexpected_exception_in_closed_leaves_no_probe_debt(self):
        b = self.make(expected=(ValueError,))
        for _ in range(3):
            with self.assertRaises(KeyError):
                b.call(lambda: {}["x"])
        self.trip(b)
        self.clock.t = T0 + 30
        self.assertTrue(b.allow())
        self.assertFalse(b.allow())

    def test_r9_expected_may_be_a_single_class(self):
        b = self.make(threshold=1, expected=ValueError)
        with self.assertRaises(ValueError):
            b.call(lambda: int("x"))
        self.assertEqual(b.state, "open")

    # Random operation sequences (seeded): invariants that follow from R2-R8

    def test_r2_to_r8_random_sequences_keep_invariants(self):
        for seed in range(5):
            rng = random.Random(seed)
            self.clock.t = T0
            b = self.make(threshold=rng.randint(1, 4), window=rng.choice([3, 10]), cooldown=rng.choice([5, 20]),
                          half_open_successes=2, probe_limit=3)
            for _ in range(400):
                self.clock.t += rng.choice([0, 0, 0.5, 1, 4, 7, 25])
                op = rng.choice(["fail", "ok", "allow", "allow", "state", "reset" if rng.random() < 0.05 else "ok"])
                if op == "fail":
                    b.record_failure()
                elif op == "ok":
                    b.record_success()
                elif op == "allow":
                    allowed = b.allow()
                    if b.state == "closed":
                        self.assertTrue(allowed)
                    if b.state == "open":
                        self.assertFalse(allowed)
                elif op == "reset":
                    b.reset()
                    self.assertEqual(b.state, "closed")
                state = b.state
                log = b.transitions
                self.assertEqual(state, log[-1][2] if log else "closed")
                prev_state, prev_time = "closed", T0
                for at, frm, to in log:
                    self.assertEqual(frm, prev_state)
                    self.assertNotEqual(frm, to)
                    self.assertGreaterEqual(at, prev_time)
                    self.assertLessEqual(at, self.clock.t)
                    if (frm, to) == ("open", "half_open"):
                        self.assertEqual(at - prev_time, b.cooldown)
                    prev_state, prev_time = to, at
                left = b.retry_after()
                if state == "open":
                    self.assertTrue(0 < left <= b.cooldown)
                else:
                    self.assertEqual(left, 0.0)


if __name__ == "__main__":
    unittest.main()
