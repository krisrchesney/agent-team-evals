"""scripts/plot.py builds its three charts from a tiny record list. Skipped when matplotlib is missing."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

HAVE_MPL = importlib.util.find_spec("matplotlib") is not None


def rec(task, cfg, passed, dry=False, stages=None):
    toks = {"input": 10, "output": 100, "cache_read": 4000, "cache_creation": 400}
    return {"task_id": task, "config_id": cfg, "rep": 1, "passed": passed, "status": "passed" if passed else "failed",
            "dry_run": dry, "tokens": toks, "num_turns": 5, "agent_wall_s": 9.0, "api_equiv_usd": 0.1,
            "tests": {"total": 2, "passed": 2, "failed": 0, "errors": 0}, "fix_round": False, "auth": "subscription",
            "stages": stages or [{"name": "solve", "tokens": toks}], "leak_suspected": [],
            "read_only_violations": [], "run_id": "x", "error": None}


class TestPlot(unittest.TestCase):
    @unittest.skipUnless(HAVE_MPL, "matplotlib not installed")
    def test_three_charts_are_written(self):
        import plot
        three = [{"name": "plan", "tokens": {"input": 1, "output": 1, "cache_read": 100, "cache_creation": 0}},
                 {"name": "build_1", "tokens": {"input": 1, "output": 1, "cache_read": 300, "cache_creation": 0}},
                 {"name": "review", "tokens": {"input": 1, "output": 1, "cache_read": 100, "cache_creation": 0}}]
        records = [rec("t1", "A", True), rec("t1", "B", True), rec("t2", "A", False), rec("t2", "B", True),
                   rec("t1", "C", True, stages=three), rec("t2", "C", True, stages=three)]
        with tempfile.TemporaryDirectory() as tmp:
            paths = plot.make_figures(records, tmp)
            self.assertEqual([p.name for p in paths],
                             ["pass_vs_usage.png", "per_task_grid.png", "tokens_by_stage.png"])
            for p in paths:
                self.assertTrue(p.exists() and p.stat().st_size > 2000, p)

    @unittest.skipUnless(HAVE_MPL, "matplotlib not installed")
    def test_dry_run_records_still_chart(self):
        import plot
        with tempfile.TemporaryDirectory() as tmp:
            paths = plot.make_figures([rec("t1", "A", True, dry=True), rec("t1", "B", True, dry=True)], tmp)
            self.assertTrue(all(p.stat().st_size > 2000 for p in paths))

    def test_stage_names_group_into_four_stages(self):
        import plot
        self.assertEqual([plot.stage_group(n) for n in ("solve", "plan", "build_2", "review", "fix")],
                         ["build", "plan", "build", "review", "fix"])

    def test_colour_follows_the_config(self):
        import plot
        self.assertEqual(plot.color_for("B", ["A", "B", "C"]), plot.color_for("B", ["B", "C"]))


if __name__ == "__main__":
    unittest.main()
