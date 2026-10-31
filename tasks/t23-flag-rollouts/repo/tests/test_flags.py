import io
import json
import os
import tempfile
import unittest

from flagkit import Context, FlagClient, FlagConfigError, UnknownFlag
from flagkit.cli import main
from flagkit.clock import FixedClock


class FlagTest(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.client = FlagClient(clock=self.clock)

    def test_boolean(self):
        self.client.add({"key": "a", "type": "boolean", "value": True})
        self.assertTrue(self.client.is_on("a"))
        self.assertEqual(self.client.evaluate("a").reason, "static")

    def test_disabled_wins(self):
        self.client.add({"key": "a", "type": "boolean", "value": True, "enabled": False})
        self.assertEqual(self.client.evaluate("a").reason, "disabled")

    def test_rollout_edges(self):
        self.client.add({"key": "r", "type": "rollout", "percent": 0})
        self.client.add({"key": "s", "type": "rollout", "percent": 100})
        self.assertFalse(self.client.is_on("r", Context("u1")))
        self.assertTrue(self.client.is_on("s", Context("u1")))

    def test_rollout_is_sticky(self):
        self.client.add({"key": "r", "type": "rollout", "percent": 10})
        self.client.add({"key": "s", "type": "rollout", "percent": 20, "salt": "r"})
        for n in range(300):
            ctx = Context(f"u{n}")
            if self.client.is_on("r", ctx):
                self.assertTrue(self.client.is_on("s", ctx))

    def test_override(self):
        self.client.add({"key": "r", "type": "rollout", "percent": 0, "overrides": {"vip": True}})
        d = self.client.evaluate("r", Context("vip"))
        self.assertEqual((d.on, d.reason), (True, "override"))

    def test_schedule(self):
        self.client.add({"key": "w", "type": "schedule", "start": "2026-03-02T12:00:00Z",
                         "end": "2026-03-02T13:00:00Z"})
        self.assertTrue(self.client.is_on("w"))
        self.clock.advance(hours=1)
        self.assertFalse(self.client.is_on("w"))

    def test_segment(self):
        self.client.add({"key": "p", "type": "segment", "attr": "plan", "values": ["pro"]})
        self.assertTrue(self.client.is_on("p", Context("u", {"plan": "pro"})))
        self.assertFalse(self.client.is_on("p", Context("u", {"plan": "free"})))

    def test_config_errors(self):
        with self.assertRaises(FlagConfigError) as ctx:
            self.client.add({"key": "x", "type": "rollout", "percent": 101})
        self.assertEqual((ctx.exception.flag, ctx.exception.field), ("x", "percent"))
        with self.assertRaises(FlagConfigError):
            self.client.add({"key": "y", "type": "nope"})

    def test_unknown_flag_and_exposures(self):
        with self.assertRaises(UnknownFlag):
            self.client.is_on("missing")
        self.client.add({"key": "a", "type": "boolean", "value": True})
        self.client.is_on("a", Context("u9"))
        self.assertEqual(self.client.exposures[-1]["user"], "u9")

    def test_to_dict_round_trip(self):
        spec = {"key": "w", "type": "schedule", "enabled": True, "salt": "w", "overrides": {"a": True},
                "start": "2026-03-02T12:00:00Z", "end": "2026-03-02T13:00:00Z"}
        self.client.add(spec)
        self.assertEqual(self.client.dump(), [spec])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "flags.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([{"key": "a", "type": "boolean", "value": True}], fh)
            out = io.StringIO()
            self.assertEqual(main([path, "--user", "u1"], stdout=out), 0)
            self.assertTrue(json.loads(out.getvalue())["a"]["on"])


if __name__ == "__main__":
    unittest.main()
