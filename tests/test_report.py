"""Tests for the paired comparison in ate/report.py (no API calls, no files)."""
import unittest

from ate import report


def rec(task, cfg, passed, tokens=1000, rep=1, status=None):
    return {"task_id": task, "config_id": cfg, "rep": rep, "passed": passed,
            "status": status or ("passed" if passed else "failed"), "dry_run": False,
            "tests": {"total": 2, "passed": 2 if passed else 1, "failed": 0, "errors": 0},
            "tokens": {"input": 0, "output": tokens // 10, "cache_read": tokens - tokens // 10,
                       "cache_creation": 0},
            "num_turns": 5, "agent_wall_s": 10.0, "api_equiv_usd": 0.1, "fix_round": False,
            "leak_suspected": [], "read_only_violations": [], "run_id": "x", "error": None,
            "auth": "subscription"}


def records():
    """Three tasks, 2 runs each. A fails both runs on t3; B and C pass everything. C costs 3x A, B 2x."""
    out = []
    for t in ("t1", "t2", "t3"):
        for rep in (1, 2):
            out.append(rec(t, "A", t != "t3", tokens=1000, rep=rep))
            out.append(rec(t, "B", True, tokens=2000, rep=rep))
            out.append(rec(t, "C", True, tokens=3000, rep=rep))
    return out


class TestPaired(unittest.TestCase):
    def test_pass_rate_difference_has_a_known_answer(self):
        res = report.paired_difference(records(), "B", "A", "pass_rate")
        # per task B - A = 0, 0, 1  ->  mean 1/3
        self.assertAlmostEqual(res["diff"], 1 / 3)
        self.assertEqual(res["tasks"], 3)
        self.assertLessEqual(res["lo"], res["diff"])
        self.assertGreaterEqual(res["hi"], res["diff"])
        self.assertGreaterEqual(res["lo"], 0.0)       # no resample can go below the smallest task difference
        self.assertLessEqual(res["hi"], 1.0)

    def test_identical_configs_have_a_zero_interval(self):
        res = report.paired_difference(records(), "C", "B", "pass_rate")
        self.assertEqual((res["diff"], res["lo"], res["hi"]), (0.0, 0.0, 0.0))

    def test_tokens_difference_is_exact_when_every_task_agrees(self):
        res = report.paired_difference(records(), "C", "A", "tokens_per_run")
        self.assertEqual((res["diff"], res["lo"], res["hi"]), (2000.0, 2000.0, 2000.0))

    def test_tokens_per_passed_task_skips_tasks_with_no_pass(self):
        res = report.paired_difference(records(), "B", "A", "tokens_per_pass")
        self.assertEqual(res["tasks"], 2)   # t3 has no A pass, so it is skipped
        # tokens per passed task = tokens summed over the task's runs / its passes: B 4000/2, A 2000/2
        self.assertEqual(res["diff"], 2000 - 1000)

    def test_same_seed_gives_identical_output(self):
        a = report.render_paired(records())
        b = report.render_paired(records())
        self.assertEqual(a, b)
        self.assertEqual(report.paired_difference(records(), "B", "A", "pass_rate"),
                         report.paired_difference(records(), "B", "A", "pass_rate"))

    def test_different_seed_may_change_the_interval_but_not_the_mean(self):
        r1 = report.paired_difference(records(), "B", "A", "pass_rate", seed=1)
        r2 = report.paired_difference(records(), "B", "A", "pass_rate", seed=2)
        self.assertEqual(r1["diff"], r2["diff"])

    def test_pairs_are_listed_as_b_a_c_a_c_b(self):
        self.assertEqual(report.paired_pairs(records()), [("B", "A"), ("C", "A"), ("C", "B")])

    def test_one_config_only_prints_nothing(self):
        only_a = [r for r in records() if r["config_id"] == "A"]
        self.assertEqual(report.paired_pairs(only_a), [])
        self.assertEqual(report.render_paired(only_a), "")
        self.assertNotIn("Paired", report.render(only_a))

    def test_task_missing_a_config_is_skipped(self):
        recs = [r for r in records() if not (r["task_id"] == "t2" and r["config_id"] == "B")]
        res = report.paired_difference(recs, "B", "A", "pass_rate")
        self.assertEqual(res["tasks"], 2)

    def test_no_shared_task_gives_none_and_na_in_the_table(self):
        self.assertIsNone(report.paired_difference(
            [rec("t1", "A", True), rec("t2", "B", True)], "B", "A", "pass_rate"))
        table = report.render_paired([rec("t1", "A", True), rec("t2", "B", True)])
        self.assertIn("n/a", table)

    def test_zero_passes_means_tokens_per_pass_is_na(self):
        recs = [rec("t1", "A", False), rec("t1", "B", False)]
        self.assertIsNone(report.paired_difference(recs, "B", "A", "tokens_per_pass"))
        text = report.render_paired(recs)
        self.assertIn("n/a", text)

    def test_retryable_runs_are_left_out_of_the_pairing(self):
        recs = records() + [rec("t3", "A", True, rep=3, status="rate_limited")]
        res = report.paired_difference(recs, "B", "A", "pass_rate")
        self.assertAlmostEqual(res["diff"], 1 / 3)   # the rate-limited "pass" must not count

    def test_render_includes_the_section_and_explains_zero(self):
        text = report.render(records())
        self.assertIn("Paired comparison", text)
        self.assertIn("| B - A | 3 |", text)
        self.assertIn("includes 0", text)
        self.assertNotIn("$", report.render_paired(records()))   # usage metrics only, no dollars


if __name__ == "__main__":
    unittest.main()
