import unittest

from jobflow import ConfigError, load_jobs, run
from jobflow.report import render


class TestJobflow(unittest.TestCase):
    def spec(self, *jobs):
        return {"jobs": list(jobs)}

    def test_runs_in_dependency_order(self):
        jobs = load_jobs(self.spec(
            {"name": "b", "action": "echo", "deps": ["a"]},
            {"name": "a", "action": "echo"},
        ))
        self.assertEqual([r.name for r in run(jobs)], ["a", "b"])

    def test_failure_skips_dependents(self):
        jobs = load_jobs(self.spec(
            {"name": "a", "action": "fail", "args": {"message": "boom"}},
            {"name": "b", "action": "echo", "deps": ["a"]},
        ))
        results = run(jobs)
        self.assertEqual([r.status for r in results], ["failed", "skipped"])
        self.assertIn("a: failed: boom", render(results))

    def test_cycle_is_a_config_error(self):
        with self.assertRaises(ConfigError):
            load_jobs(self.spec(
                {"name": "a", "action": "echo", "deps": ["b"]},
                {"name": "b", "action": "echo", "deps": ["a"]},
            ))


if __name__ == "__main__":
    unittest.main()
