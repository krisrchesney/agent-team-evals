"""Hidden tests for t35-rate-limits. Every rule is in docs/SPEC.md; see AUDIT.md."""
import copy
import json
import os
import tempfile
import unittest

from ratelimit import (FixedClock, JsonFileStore, Limiter, MemoryStore, SlidingWindow, StoreCorrupt, TokenBucket,
                       UnknownRule)

T0 = 1000.0


class CountingClock:
    """Every call to now() moves time forward by one second."""

    def __init__(self, start=T0):
        self.t = start
        self.calls = 0

    def now(self):
        self.calls += 1
        self.t += 1.0
        return self.t


class TestTokenBucket(unittest.TestCase):
    def setUp(self):
        self.rule = TokenBucket(5, 2)

    def ev(self, state, now, cost=1, skew=2.0):
        return self.rule.evaluate(state, now, cost, skew)

    def test_fresh_key_starts_full(self):
        d, s = self.ev(None, T0)
        self.assertEqual((d.allowed, d.limit, d.remaining, d.retry_after, d.reset_after), (True, 5, 4, 0.0, 0.5))
        self.assertEqual(s, {"tokens": 4.0, "updated": T0})

    def test_drain_then_deny(self):
        s = None
        for _ in range(5):
            d, s = self.ev(s, T0)
        self.assertTrue(d.allowed)
        d, s = self.ev(s, T0)
        self.assertEqual((d.allowed, d.remaining, d.retry_after, d.reset_after), (False, 0, 0.5, 2.5))
        self.assertEqual(s, {"tokens": 0.0, "updated": T0})

    def test_refill_is_linear_and_capped(self):
        s = {"tokens": 0.0, "updated": T0}
        d, s2 = self.ev(s, T0 + 1.0)
        self.assertEqual((d.allowed, d.remaining), (True, 1))
        self.assertEqual(s2, {"tokens": 1.0, "updated": T0 + 1.0})
        d, s3 = self.ev(s, T0 + 100)
        self.assertEqual((d.remaining, s3["tokens"]), (4, 4.0))

    def test_fractional_tokens(self):
        s = {"tokens": 0.0, "updated": T0}
        d, s2 = self.ev(s, T0 + 1.25)  # 2.5 tokens, take one
        self.assertEqual((d.allowed, d.remaining, s2["tokens"]), (True, 1, 1.5))
        d, _ = self.ev(s, T0 + 1.25, cost=3)
        self.assertEqual((d.allowed, d.remaining, d.retry_after), (False, 2, 0.25))

    def test_cost_above_capacity_never_succeeds(self):
        s = {"tokens": 3.0, "updated": T0}
        d, s2 = self.ev(s, T0 + 1.0, cost=6)
        self.assertEqual((d.allowed, d.retry_after, d.remaining), (False, None, 5))
        self.assertEqual(s2, {"tokens": 5.0, "updated": T0 + 1.0})

    def test_state_is_not_mutated(self):
        s = {"tokens": 1.0, "updated": T0}
        before = copy.deepcopy(s)
        self.ev(s, T0 + 5)
        self.assertEqual(s, before)

    def test_backwards_within_skew_neither_refills_nor_moves_updated(self):
        s = {"tokens": 1.0, "updated": T0 + 1.0}
        d, s2 = self.ev(s, T0)
        self.assertEqual((d.allowed, s2), (True, {"tokens": 0.0, "updated": T0 + 1.0}))
        d, s3 = self.ev(s2, T0 + 2.0)  # one second past the stored time
        self.assertEqual(s3, {"tokens": 1.0, "updated": T0 + 2.0})

    def test_backwards_beyond_skew_resets_the_anchor(self):
        s = {"tokens": 0.0, "updated": T0 + 10.0}
        d, s2 = self.ev(s, T0)
        self.assertEqual((d.allowed, d.retry_after), (False, 0.5))
        self.assertEqual(s2, {"tokens": 0.0, "updated": T0})
        d, _ = self.ev(s2, T0 + 0.5)
        self.assertTrue(d.allowed)

    def test_skew_boundary_is_inclusive(self):
        s = {"tokens": 0.0, "updated": T0 + 2.0}
        _, s2 = self.ev(s, T0, skew=2.0)
        self.assertEqual(s2["updated"], T0 + 2.0)
        _, s3 = self.ev(s, T0, skew=1.9)
        self.assertEqual(s3["updated"], T0)

    def test_is_idle(self):
        self.assertTrue(self.rule.is_idle(None, T0, 2.0))
        s = {"tokens": 3.0, "updated": T0}
        self.assertFalse(self.rule.is_idle(s, T0, 2.0))
        self.assertFalse(self.rule.is_idle(s, T0 + 0.5, 2.0))
        self.assertTrue(self.rule.is_idle(s, T0 + 1.0, 2.0))

    def test_validation(self):
        for cap in (0, -1, True, 1.5, "5"):
            with self.assertRaises(ValueError):
                TokenBucket(cap, 1)
        for rate in (0, -1, True, "1", None):
            with self.assertRaises(ValueError):
                TokenBucket(5, rate)
        for cost in (0, -1, True, 1.0, "1"):
            with self.assertRaises(ValueError):
                self.ev(None, T0, cost=cost)
        TokenBucket(1, 0.25)


class TestSlidingWindow(unittest.TestCase):
    def setUp(self):
        self.rule = SlidingWindow(3, 10)

    def ev(self, state, now, cost=1, skew=2.0):
        return self.rule.evaluate(state, now, cost, skew)

    def test_allows_up_to_limit_then_denies(self):
        s = None
        seen = []
        for t in (0, 1, 2):
            d, s = self.ev(s, T0 + t)
            seen.append((d.allowed, d.remaining, d.retry_after))
        self.assertEqual(seen, [(True, 2, 0.0), (True, 1, 0.0), (True, 0, 0.0)])
        d, s2 = self.ev(s, T0 + 3)
        self.assertEqual((d.allowed, d.limit, d.remaining, d.retry_after, d.reset_after), (False, 3, 0, 7.0, 9.0))
        self.assertEqual(s2, s)

    def test_hit_expires_exactly_at_window(self):
        s = {"hits": [T0]}
        d, s2 = self.ev(s, T0 + 9.5)
        self.assertEqual(s2["hits"], [T0, T0 + 9.5])
        d, s3 = self.ev(s, T0 + 10)
        self.assertEqual(s3["hits"], [T0 + 10])

    def test_cost_adds_that_many_hits(self):
        d, s = self.ev(None, T0, cost=2)
        self.assertEqual((d.allowed, d.remaining, d.reset_after), (True, 1, 10.0))
        self.assertEqual(s["hits"], [T0, T0])

    def test_retry_after_waits_for_enough_hits_to_expire(self):
        s = {"hits": [T0, T0 + 4, T0 + 6]}
        d, _ = self.ev(s, T0 + 7, cost=1)
        self.assertEqual(d.retry_after, 3.0)
        d, _ = self.ev(s, T0 + 7, cost=2)
        self.assertEqual(d.retry_after, 7.0)
        d, _ = self.ev(s, T0 + 7, cost=3)
        self.assertEqual(d.retry_after, 9.0)

    def test_cost_above_limit_never_succeeds(self):
        s = {"hits": [T0]}
        d, s2 = self.ev(s, T0 + 20, cost=4)
        self.assertEqual((d.allowed, d.retry_after, d.remaining, d.reset_after), (False, None, 3, 0.0))
        self.assertEqual(s2, {"hits": []})

    def test_denied_request_adds_nothing(self):
        s = {"hits": [T0, T0, T0]}
        _, s2 = self.ev(s, T0 + 1)
        self.assertEqual(s2, s)

    def test_state_is_not_mutated(self):
        s = {"hits": [T0, T0 + 1]}
        before = copy.deepcopy(s)
        self.ev(s, T0 + 2)
        self.assertEqual(s, before)

    def test_future_hits_within_skew_stay(self):
        s = {"hits": [T0 + 1.0]}
        d, s2 = self.ev(s, T0)
        self.assertEqual(s2["hits"], [T0, T0 + 1.0])
        self.assertEqual(d.reset_after, 11.0)

    def test_future_hits_beyond_skew_move_to_now_and_list_is_sorted(self):
        s = {"hits": [T0 + 1.0, T0 + 10.0]}
        d, s2 = self.ev(s, T0)
        self.assertEqual(s2["hits"], [T0, T0, T0 + 1.0])
        self.assertEqual((d.allowed, d.remaining), (True, 0))

    def test_is_idle(self):
        self.assertTrue(self.rule.is_idle(None, T0, 2.0))
        self.assertFalse(self.rule.is_idle({"hits": [T0]}, T0 + 9, 2.0))
        self.assertTrue(self.rule.is_idle({"hits": [T0]}, T0 + 10, 2.0))

    def test_validation(self):
        for limit in (0, -1, True, 2.5):
            with self.assertRaises(ValueError):
                SlidingWindow(limit, 10)
        for window in (0, -5, True, "10"):
            with self.assertRaises(ValueError):
                SlidingWindow(3, window)
        for cost in (0, True, 2.0):
            with self.assertRaises(ValueError):
                self.ev(None, T0, cost=cost)


class LimiterBase(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock(T0)
        self.store = MemoryStore()
        self.lim = Limiter({"sec": TokenBucket(2, 1), "min": SlidingWindow(5, 60)}, store=self.store, clock=self.clock)


class TestLimiter(LimiterBase):
    def test_hit_saves_state_even_when_denied(self):
        self.lim.hit("sec", "a")
        self.lim.hit("sec", "a")
        self.clock.advance(0.5)
        d = self.lim.hit("sec", "a")
        self.assertFalse(d.allowed)
        self.assertEqual(self.store.get("sec", "a"), {"tokens": 0.5, "updated": T0 + 0.5})

    def test_keys_are_independent(self):
        self.lim.hit("sec", "a")
        self.lim.hit("sec", "a")
        self.assertFalse(self.lim.hit("sec", "a").allowed)
        self.assertTrue(self.lim.hit("sec", "b").allowed)
        self.assertEqual(self.store.keys("sec"), ["a", "b"])

    def test_peek_saves_nothing_and_matches_hit(self):
        p = self.lim.peek("min", "a", cost=2)
        self.assertEqual(self.store.keys("min"), [])
        self.assertEqual(p, self.lim.hit("min", "a", cost=2))

    def test_unknown_rule(self):
        for call in (lambda: self.lim.hit("nope", "a"), lambda: self.lim.peek("nope", "a"),
                     lambda: self.lim.reset("nope"), lambda: self.lim.hit_all([("sec", "a"), ("nope", "a")])):
            with self.assertRaises(UnknownRule):
                call()
        self.assertEqual(self.store.keys("sec"), [])

    def test_bad_key_or_cost_changes_nothing(self):
        for key in ("", None, 5, b"a"):
            with self.assertRaises(ValueError):
                self.lim.hit("sec", key)
            with self.assertRaises(ValueError):
                self.lim.peek("sec", key)
        for cost in (0, True, 1.5):
            with self.assertRaises(ValueError):
                self.lim.hit("sec", "a", cost=cost)
        self.assertEqual(self.store.keys("sec"), [])

    def test_clock_is_read_once_per_call(self):
        clock = CountingClock()
        lim = Limiter({"sec": TokenBucket(2, 1), "min": SlidingWindow(5, 60)}, clock=clock)
        lim.hit("sec", "a")
        lim.peek("sec", "a")
        lim.hit_all([("sec", "a"), ("min", "a")])
        lim.purge()
        lim.reset("sec", "a")  # reset does not read the clock
        self.assertEqual(clock.calls, 4)

    def test_hit_all_uses_one_now_for_every_pair(self):
        clock = CountingClock()
        store = MemoryStore()
        lim = Limiter({"sec": TokenBucket(2, 1), "min": SlidingWindow(5, 60)}, store=store, clock=clock)
        lim.hit_all([("sec", "a"), ("min", "a")])
        self.assertEqual(store.get("sec", "a")["updated"], T0 + 1.0)
        self.assertEqual(store.get("min", "a")["hits"], [T0 + 1.0])

    def test_max_skew_is_passed_to_the_rules(self):
        lim = Limiter({"sec": TokenBucket(2, 1)}, store=self.store, clock=self.clock, max_skew=30)
        self.store.set("sec", "a", {"tokens": 0.0, "updated": T0 + 20})
        d = lim.hit("sec", "a")
        self.assertFalse(d.allowed)
        self.assertEqual(self.store.get("sec", "a")["updated"], T0 + 20)

    def test_decision_headers_from_a_denial(self):
        self.lim.hit("sec", "a", cost=2)
        h = self.lim.hit("sec", "a").headers()
        self.assertEqual(h, {"X-RateLimit-Limit": "2", "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "2",
                             "Retry-After": "1"})


class TestHitAll(LimiterBase):
    def test_all_allowed_returns_smallest_remaining_and_saves_all(self):
        d = self.lim.hit_all([("sec", "a"), ("min", "a")])
        self.assertEqual((d.limit, d.remaining), (2, 1))
        d = self.lim.hit_all([("sec", "a"), ("min", "a")])
        self.assertEqual((d.limit, d.remaining), (2, 0))
        self.assertEqual(len(self.store.get("min", "a")["hits"]), 2)

    def test_tie_returns_the_first(self):
        lim = Limiter({"x": TokenBucket(3, 1), "y": SlidingWindow(3, 60)}, clock=self.clock)
        d = lim.hit_all([("y", "k"), ("x", "k")])
        self.assertEqual(d.limit, 3)
        self.assertEqual(d.reset_after, 60.0)

    def test_any_denial_saves_nothing(self):
        self.lim.hit_all([("sec", "a"), ("min", "a")])
        self.lim.hit_all([("sec", "a"), ("min", "a")])
        before = (self.store.get("sec", "a"), self.store.get("min", "a"))
        d = self.lim.hit_all([("min", "a"), ("sec", "a")])
        self.assertFalse(d.allowed)
        self.assertEqual((d.limit, d.retry_after), (2, 1.0))
        self.assertEqual((self.store.get("sec", "a"), self.store.get("min", "a")), before)

    def test_denial_with_largest_retry_after_wins(self):
        for _ in range(5):
            self.lim.hit("min", "a")
        self.lim.hit("sec", "a", cost=2)
        d = self.lim.hit_all([("sec", "a"), ("min", "a")])
        self.assertEqual((d.allowed, d.limit, d.retry_after), (False, 5, 60.0))

    def test_never_succeeding_denial_beats_numbers(self):
        for _ in range(5):
            self.lim.hit("min", "a")
        d = self.lim.hit_all([("min", "a"), ("sec", "a")], cost=3)
        self.assertEqual((d.allowed, d.retry_after, d.limit), (False, None, 2))

    def test_bad_arguments(self):
        for pairs in ([], [("sec", "a"), ("sec", "a")]):
            with self.assertRaises(ValueError):
                self.lim.hit_all(pairs)
        with self.assertRaises(ValueError):
            self.lim.hit_all([("sec", "a"), ("min", "")])
        with self.assertRaises(ValueError):
            self.lim.hit_all([("sec", "a")], cost=0)
        self.assertEqual(self.store.keys("sec") + self.store.keys("min"), [])



class TestResetAndPurge(LimiterBase):
    def test_reset_key_and_rule(self):
        for key in ("a", "b"):
            self.lim.hit("sec", key)
        self.lim.hit("min", "a")
        self.assertIsNone(self.lim.reset("sec", "a"))
        self.assertEqual(self.store.keys("sec"), ["b"])
        self.lim.reset("sec")
        self.assertEqual(self.store.keys("sec"), [])
        self.assertEqual(self.store.keys("min"), ["a"])
        self.lim.reset("sec", "never-seen")

    def test_purge_removes_only_idle_entries(self):
        self.lim.hit("sec", "a")
        self.lim.hit("sec", "b", cost=2)
        self.lim.hit("min", "a")
        self.clock.advance(1.0)
        self.assertEqual(self.lim.purge(), 1)  # a: bucket full again; b: needs 2s; min/a: window open
        self.assertEqual(self.store.keys("sec"), ["b"])
        self.clock.advance(100)
        self.assertEqual(self.lim.purge(), 2)
        self.assertEqual(self.store.keys("sec") + self.store.keys("min"), [])

    def test_purge_leaves_unknown_rules_alone(self):
        self.store.set("old-rule", "k", {"tokens": 5.0, "updated": 0.0})
        self.assertEqual(self.lim.purge(), 0)
        self.assertEqual(self.store.keys("old-rule"), ["k"])


class TestJsonFileStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "state", "limits.json")
        self.store = JsonFileStore(self.path)

    def doc(self):
        with open(self.path, encoding="utf-8") as fh:
            return json.load(fh)

    def test_missing_file_is_empty_and_reading_does_not_create_it(self):
        self.assertIsNone(self.store.get("r", "k"))
        self.assertEqual(self.store.keys("r"), [])
        self.store.delete("r", "k")
        self.store.delete_rule("r")
        self.assertFalse(os.path.exists(self.path))
        self.assertFalse(os.path.exists(os.path.dirname(self.path)))

    def test_set_creates_parent_dirs_and_the_documented_layout(self):
        self.store.set("r", "k", {"tokens": 1.5, "updated": 3.0})
        self.store.set("r", "j", {"hits": [1.0]})
        self.assertEqual(self.doc(), {"version": 1, "rules": {"r": {"k": {"tokens": 1.5, "updated": 3.0},
                                                                    "j": {"hits": [1.0]}}}})
        with open(self.path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), json.dumps(self.doc(), sort_keys=True))

    def test_no_tmp_file_left_behind(self):
        self.store.set("r", "k", {})
        self.store.delete("r", "k")
        self.store.set("r", "k", {})
        self.assertEqual(sorted(os.listdir(os.path.dirname(self.path))), ["limits.json"])

    def test_sees_changes_made_through_another_object(self):
        other = JsonFileStore(self.path)
        self.store.set("r", "k", {"n": 1})
        self.assertEqual(other.get("r", "k"), {"n": 1})
        other.set("r", "k", {"n": 2})
        other.set("r", "z", {"n": 3})
        self.assertEqual(self.store.get("r", "k"), {"n": 2})
        self.assertEqual(self.store.keys("r"), ["k", "z"])

    def test_delete_removes_empty_rules(self):
        self.store.set("a", "1", {})
        self.store.set("b", "1", {})
        self.store.delete("a", "1")
        self.assertEqual(self.doc()["rules"], {"b": {"1": {}}})
        self.store.delete("b", "missing")
        self.store.delete_rule("b")
        self.assertEqual(self.doc(), {"version": 1, "rules": {}})

    def test_get_returns_a_fresh_dict(self):
        self.store.set("r", "k", {"hits": [1.0]})
        got = self.store.get("r", "k")
        got["hits"].append(2.0)
        self.assertEqual(self.store.get("r", "k"), {"hits": [1.0]})

    def test_corrupt_files_raise_everywhere_and_stay_untouched(self):
        os.makedirs(os.path.dirname(self.path))
        for content in ("{not json", "[]", '{"version": 2, "rules": {}}', '{"version": 1}', '{"version": 1, "rules": []}',
                        ""):
            with self.subTest(content=content):
                with open(self.path, "w", encoding="utf-8") as fh:
                    fh.write(content)
                for call in (lambda: self.store.get("r", "k"), lambda: self.store.keys("r"),
                             lambda: self.store.set("r", "k", {}), lambda: self.store.delete("r", "k"),
                             lambda: self.store.delete_rule("r")):
                    with self.assertRaises(StoreCorrupt):
                        call()
                with open(self.path, encoding="utf-8") as fh:
                    self.assertEqual(fh.read(), content)

    def test_limiter_state_survives_a_restart(self):
        clock = FixedClock(T0)
        rules = {"sec": TokenBucket(2, 1)}
        Limiter(rules, store=JsonFileStore(self.path), clock=clock).hit("sec", "a", cost=2)
        clock.advance(0.5)
        d = Limiter(rules, store=JsonFileStore(self.path), clock=clock).hit("sec", "a")
        self.assertEqual((d.allowed, d.retry_after), (False, 0.5))

    def test_skew_between_processes(self):
        rules = {"sec": TokenBucket(2, 1), "min": SlidingWindow(2, 60)}
        a = Limiter(rules, store=JsonFileStore(self.path), clock=FixedClock(T0 + 100))
        a.hit("sec", "k", cost=2)
        a.hit("min", "k")
        a.hit("min", "k")
        slow = Limiter(rules, store=JsonFileStore(self.path), clock=FixedClock(T0))  # clock 100 s behind
        d = slow.hit("sec", "k")
        self.assertEqual((d.allowed, d.retry_after), (False, 1.0))
        d = slow.hit("min", "k")  # stored hits were moved to the slow clock's now, so they last a full window
        self.assertEqual((d.allowed, d.retry_after), (False, 60.0))

    def test_two_limiters_share_one_file(self):
        clock = FixedClock(T0)
        rules = {"min": SlidingWindow(3, 60)}
        one = Limiter(rules, store=JsonFileStore(self.path), clock=clock)
        two = Limiter(rules, store=JsonFileStore(self.path), clock=clock)
        one.hit("min", "k")
        two.hit("min", "k")
        one.hit("min", "k")
        self.assertFalse(two.hit("min", "k").allowed)


if __name__ == "__main__":
    unittest.main()
