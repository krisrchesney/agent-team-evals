"""Hidden tests for t23-flag-rollouts. Every rule is shown by the starting code; see AUDIT.md."""
import copy
import io
import json
import os
import tempfile
import unittest

from flagkit import Context, FlagClient, FlagConfigError
from flagkit.cli import main
from flagkit.clock import FixedClock
from flagkit.hashing import bucket

# FixedClock starts at 2026-03-02T12:00:00Z
EARLY = "2026-03-02T11:00:00Z"
NOW = "2026-03-02T12:00:00Z"
MID = "2026-03-02T12:30:00Z"
LATE = "2026-03-02T13:00:00Z"
SALT = "ramp-salt"


def user_with_bucket(salt, wanted):
    for n in range(2_000_000):
        user = f"user-{n}"
        if bucket(salt, user) == wanted:
            return user
    raise AssertionError(f"no user with bucket {wanted}")


def ramp(steps, key="rampy", **extra):
    spec = {"key": key, "type": "ramp", "salt": SALT, "steps": steps}
    spec.update(extra)
    return spec


def step(at, percent):
    return {"at": at, "percent": percent}


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.client = FlagClient(clock=self.clock)

    def on(self, user, key="rampy"):
        return self.client.evaluate(key, Context(user_id=user))


class TestRegistration(Base):
    def test_ramp_is_a_supported_type(self):
        self.assertIn("ramp", FlagClient.supported_types())
        self.assertTrue({"boolean", "rollout", "schedule", "segment"} <= set(FlagClient.supported_types()))

    def test_existing_types_unchanged(self):
        self.client.add({"key": "r", "type": "rollout", "percent": 100})
        self.client.add({"key": "b", "type": "boolean", "value": True})
        self.assertEqual(self.client.evaluate("r", Context("u")).reason, "rollout")
        self.assertEqual(self.client.evaluate("b", Context("u")).reason, "static")


class TestPercentage(Base):
    def test_before_the_first_step_nobody_is_in(self):
        self.client.add(ramp([step(LATE, 100)]))
        d = self.on(user_with_bucket(SALT, 0))
        self.assertEqual((d.on, d.reason), (False, "outside_ramp"))

    def test_latest_started_step_wins_whatever_the_order(self):
        self.client.add(ramp([step(LATE, 90), step(EARLY, 10), step(MID, 50)]))
        low = user_with_bucket(SALT, 999)    # in at 10%
        high = user_with_bucket(SALT, 1000)  # out at 10%, in at 50%
        self.assertTrue(self.on(low).on)
        self.assertFalse(self.on(high).on)
        self.clock.advance(minutes=30)       # 12:30, the 50% step has started
        self.assertTrue(self.on(high).on)

    def test_a_step_counts_from_the_moment_it_starts(self):
        self.client.add(ramp([step(NOW, 100)]))
        self.assertTrue(self.on("anyone").on)

    def test_one_second_before_a_step_is_not_enough(self):
        self.client.add(ramp([step("2026-03-02T12:00:01Z", 100)]))
        self.assertFalse(self.on("anyone").on)
        self.clock.advance(seconds=1)
        self.assertTrue(self.on("anyone").on)

    def test_percentage_can_go_down(self):
        self.client.add(ramp([step(EARLY, 100), step(NOW, 0)]))
        d = self.on("anyone")
        self.assertEqual((d.on, d.reason), (False, "outside_ramp"))

    def test_last_step_holds_forever(self):
        self.client.add(ramp([step(EARLY, 100)]))
        self.clock.advance(days=900)
        self.assertTrue(self.on("anyone").on)

    def test_the_bucket_boundary_is_exclusive(self):
        self.client.add(ramp([step(EARLY, 10)]))
        self.assertTrue(self.on(user_with_bucket(SALT, 999)).on)
        self.assertFalse(self.on(user_with_bucket(SALT, 1000)).on)

    def test_fractional_percentages(self):
        self.client.add(ramp([step(EARLY, 12.5)]))
        self.assertTrue(self.on(user_with_bucket(SALT, 1249)).on)
        self.assertFalse(self.on(user_with_bucket(SALT, 1250)).on)

    def test_zero_and_hundred(self):
        self.client.add(ramp([step(EARLY, 0)], key="none"))
        self.client.add(ramp([step(EARLY, 100)], key="all"))
        self.assertFalse(self.on(user_with_bucket(SALT, 0), "none").on)
        self.assertTrue(self.on(user_with_bucket(SALT, 9999), "all").on)


class TestWhoIsIn(Base):
    def test_same_users_as_a_rollout_with_the_same_salt(self):
        other = FlagClient(clock=self.clock)
        self.client.add(ramp([step(EARLY, 37)]))
        other.add({"key": "plain", "type": "rollout", "percent": 37, "salt": SALT})
        users = [f"person-{n}" for n in range(400)]
        mine = [self.on(u).on for u in users]
        theirs = [other.evaluate("plain", Context(u)).on for u in users]
        self.assertEqual(mine, theirs)
        self.assertTrue(0 < sum(mine) < len(users))

    def test_default_salt_is_the_flag_key(self):
        other = FlagClient(clock=self.clock)
        self.client.add({"key": "same", "type": "ramp", "steps": [step(EARLY, 40)]})
        other.add({"key": "same", "type": "rollout", "percent": 40})
        for n in range(300):
            ctx = Context(f"u{n}")
            self.assertEqual(self.client.is_on("same", ctx), other.is_on("same", ctx))

    def test_users_stay_in_as_the_ramp_rises(self):
        self.client.add(ramp([step(EARLY, 10), step(MID, 20), step(LATE, 60)]))
        users = [f"person-{n}" for n in range(400)]
        seen = set()
        for _ in range(3):
            now_in = {u for u in users if self.on(u).on}
            self.assertTrue(seen <= now_in)
            seen = now_in
            self.clock.advance(minutes=45)
        self.assertGreater(len(seen), 100)

    def test_user_ids_are_compared_as_stripped_strings(self):
        self.client.add(ramp([step(EARLY, 50)]))
        user = user_with_bucket(SALT, 10)
        number = next(n for n in range(1, 500_000) if bucket(SALT, str(n)) < 5000)
        for variant in (number, str(number), f"  {number} "):
            self.assertTrue(self.on(variant).on, variant)
        self.assertTrue(self.on(f" {user}\n").on)


class TestEvaluationOrder(Base):
    def test_reasons(self):
        self.client.add(ramp([step(EARLY, 10)]))
        self.assertEqual(self.on(user_with_bucket(SALT, 5)).reason, "ramp")
        self.assertEqual(self.on(user_with_bucket(SALT, 5000)).reason, "outside_ramp")

    def test_disabled_comes_first(self):
        self.client.add(ramp([step(EARLY, 100)], enabled=False, overrides={"vip": True}))
        for user in (None, "", "vip", "someone"):
            d = self.on(user)
            self.assertEqual((d.on, d.reason), (False, "disabled"), repr(user))

    def test_anonymous_users_are_never_in(self):
        self.client.add(ramp([step(EARLY, 100)]))
        for user in (None, "", "   "):
            d = self.on(user)
            self.assertEqual((d.on, d.reason), (False, "anonymous"), repr(user))
        d = self.client.evaluate("rampy")
        self.assertEqual(d.reason, "anonymous")

    def test_override_beats_the_percentage_both_ways(self):
        self.client.add(ramp([step(EARLY, 100)], key="full", overrides={"blocked": False}))
        self.client.add(ramp([step(LATE, 100)], key="not-yet", overrides={"vip": True}))
        blocked = self.client.evaluate("full", Context("blocked"))
        self.assertEqual((blocked.on, blocked.reason), (False, "override"))
        vip = self.client.evaluate("not-yet", Context("vip"))
        self.assertEqual((vip.on, vip.reason), (True, "override"))
        self.assertEqual(self.client.evaluate("not-yet", Context("other")).reason, "outside_ramp")


class TestDefinition(Base):
    def test_to_dict(self):
        steps = [step(LATE, 60), step(EARLY, 10.5), step(MID, 20)]
        self.client.add({"key": "r", "type": "ramp", "steps": steps})
        self.assertEqual(self.client.dump(), [{
            "key": "r", "type": "ramp", "enabled": True, "salt": "r", "overrides": {},
            "steps": [step(LATE, 60), step(EARLY, 10.5), step(MID, 20)]}])

    def test_round_trip(self):
        self.client.add(ramp([step(LATE, 60), step(EARLY, 10)], overrides={"a": True}, enabled=False))
        first = self.client.dump()
        again = FlagClient(first, clock=self.clock)
        self.assertEqual(again.dump(), first)
        self.assertEqual(first[0]["salt"], SALT)

    def test_the_definition_is_not_changed(self):
        spec = ramp([step(LATE, 60), step(EARLY, 10)])
        before = copy.deepcopy(spec)
        self.client.add(spec)
        self.assertEqual(spec, before)

    def test_bad_steps_are_config_errors_on_load(self):
        bad = {
            "missing": None,
            "empty": [],
            "not a list": "2026-03-02T12:00:00Z",
            "step not a dict": ["2026-03-02T12:00:00Z"],
            "no time": [{"percent": 10}],
            "bad time": [step("2026-03-02 12:00", 10)],
            "time zone offset": [step("2026-03-02T12:00:00+00:00", 10)],
            "no percent": [{"at": EARLY}],
            "over 100": [step(EARLY, 100.5)],
            "below 0": [step(EARLY, -1)],
            "bool percent": [step(EARLY, True)],
            "string percent": [step(EARLY, "10")],
            "same time twice": [step(EARLY, 10), step(MID, 20), step(EARLY, 30)],
        }
        for name, steps in bad.items():
            spec = {"key": "bad-ramp", "type": "ramp", "steps": steps}
            if steps is None:
                del spec["steps"]
            with self.subTest(name):
                with self.assertRaises(FlagConfigError) as ctx:
                    FlagClient().add(spec)
                self.assertEqual(ctx.exception.flag, "bad-ramp")
                self.assertTrue(ctx.exception.field.startswith("steps"), ctx.exception.field)
                self.assertTrue(str(ctx.exception).startswith("flag 'bad-ramp': steps"))

    def test_a_bad_ramp_is_not_added(self):
        with self.assertRaises(FlagConfigError):
            self.client.add(ramp([]))
        self.assertEqual(self.client.flags, {})
        self.client.add(ramp([step(EARLY, 10)]))

    def test_common_fields_are_validated_too(self):
        with self.assertRaises(FlagConfigError) as ctx:
            self.client.add(ramp([step(EARLY, 10)], enabled="yes"))
        self.assertEqual(ctx.exception.field, "enabled")


class TestEverywhere(Base):
    def test_evaluate_all_and_exposures(self):
        self.client.add(ramp([step(EARLY, 100)]))
        self.client.add({"key": "b", "type": "boolean", "value": True})
        out = self.client.evaluate_all(Context("u1"))
        self.assertEqual({k: d.reason for k, d in out.items()}, {"b": "static", "rampy": "ramp"})
        self.assertEqual(self.client.exposures[-1],
                         {"flag": "rampy", "on": True, "reason": "ramp", "user": "u1"})

    def run_cli(self, flags, *argv):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "flags.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"flags": flags}, fh)
            out = io.StringIO()
            code = main([path, *argv], stdout=out)
        return code, out.getvalue()

    def test_cli_follows_the_time(self):
        flags = [ramp([step(NOW, 100)])]
        code, text = self.run_cli(flags, "--user", "u1", "--at", NOW)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["rampy"], {"flag": "rampy", "on": True, "reason": "ramp"})
        _, text = self.run_cli(flags, "--user", "u1", "--at", "2026-03-02T11:59:59Z")
        self.assertEqual(json.loads(text)["rampy"]["reason"], "outside_ramp")
        _, text = self.run_cli(flags, "--at", NOW)
        self.assertEqual(json.loads(text)["rampy"]["reason"], "anonymous")

    def test_cli_reports_a_bad_ramp(self):
        code, text = self.run_cli([{"key": "x", "type": "ramp", "steps": []}], "--user", "u1")
        self.assertEqual((code, text), (2, ""))


if __name__ == "__main__":
    unittest.main()
