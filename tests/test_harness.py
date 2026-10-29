"""Tests for the harness itself. No API calls: everything uses the dry-run fake CLI."""
import json
import tempfile
import unittest
from pathlib import Path

from ate import REPO_ROOT, claude, config, grade, pipeline, report, results, tasks, workspace


class TestConfigs(unittest.TestCase):
    def test_all_configs_load_and_reference_real_files(self):
        for cid in config.list_configs():
            cfg = config.load_config(cid)
            for st in cfg["stages"]:
                config.load_prompt(st["prompt"])
                if st.get("schema"):
                    config.load_schema(st["schema"])
            agents = config.load_agents(cfg.get("agents_dir"))
            for st in cfg["stages"]:
                if st.get("agent"):
                    self.assertIn(st["agent"], agents, f"{cid} stage {st['name']}")

    def test_shared_roles_identical_across_configs(self):
        # B and C must differ only in team structure, not in how the builder/reviewer are prompted.
        for role in ("builder.md", "reviewer.md"):
            b = (REPO_ROOT / "configs/B/.claude/agents" / role).read_text(encoding="utf-8")
            c = (REPO_ROOT / "configs/C/.claude/agents" / role).read_text(encoding="utf-8")
            self.assertEqual(b, c, role)

    def test_read_only_roles_have_no_edit_tools(self):
        for cid in ("B", "C"):
            agents = config.load_agents(config.load_config(cid)["agents_dir"])
            for name in ("reviewer", "planner"):
                if name in agents:
                    self.assertFalse({"Edit", "Write"} & set(agents[name]["tools"]), f"{cid}/{name}")
        d = config.load_defaults()
        self.assertNotIn("Edit", d["tools_read"])
        self.assertNotIn("Write", d["tools_read"])

    def test_agent_frontmatter_parse(self):
        meta = config.parse_agent_md("---\nname: x\ntools: Read, Grep\n---\nBody here\n")
        self.assertEqual(meta["tools"], ["Read", "Grep"])
        self.assertEqual(meta["prompt"], "Body here")


class TestStreamParsing(unittest.TestCase):
    def test_result_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "s.jsonl"
            log.write_text("\n".join([
                json.dumps({"type": "system", "subtype": "init"}),
                "not json",
                json.dumps({"type": "result", "subtype": "success", "is_error": False,
                            "total_cost_usd": 0.1234, "num_turns": 7, "duration_api_ms": 4200,
                            "result": "done", "session_id": "abc",
                            "usage": {"input_tokens": 10, "output_tokens": 20,
                                      "cache_read_input_tokens": 300, "cache_creation_input_tokens": 40},
                            "structured_output": {"verdict": "APPROVE", "findings": []}}),
            ]))
            res = claude.StageResult(name="review", agent="reviewer", exit_code=0)
            claude.apply_result_event(res, claude.read_result_event(log))
        self.assertAlmostEqual(res.cost_usd, 0.1234)
        self.assertEqual(res.tokens, {"input": 10, "output": 20, "cache_read": 300, "cache_creation": 40})
        self.assertEqual(res.structured["verdict"], "APPROVE")
        self.assertFalse(res.is_error)

    def test_missing_result_event_is_an_error(self):
        res = claude.StageResult(name="x", agent=None, exit_code=1)
        claude.apply_result_event(res, None)
        self.assertIn("no result event", res.error)

    def test_prompt_not_in_argv(self):
        spec = claude.StageSpec(name="s", prompt="SECRET PROMPT", cwd=Path("."), log_path=Path("x"),
                                model="sonnet", max_turns=5, budget_usd=1.0, timeout_s=10,
                                permission_mode="acceptEdits", tools="Read", allowed_tools=["Read"])
        cmd = claude.build_command("claude", spec)
        self.assertNotIn("SECRET PROMPT", cmd)
        self.assertIn("--max-budget-usd", cmd)
        self.assertIn("--max-turns", cmd)


class TestGrading(unittest.TestCase):
    def test_parse_unittest_output(self):
        ok = grade.parse_unittest_output("....\n---\nRan 4 tests in 0.01s\n\nOK\n", 0)
        self.assertTrue(ok["ok"])
        self.assertEqual(ok["passed"], 4)
        bad = grade.parse_unittest_output("Ran 5 tests in 0.1s\n\nFAILED (failures=2, errors=1)\n", 1)
        self.assertEqual((bad["passed"], bad["failed"], bad["errors"]), (2, 2, 1))
        self.assertFalse(bad["ok"])
        crash = grade.parse_unittest_output("ImportError: boom\n", 1)
        self.assertFalse(crash["ok"])

    def test_tasks_are_valid(self):
        """Hidden tests must fail on the snapshot and pass on the reference solution."""
        from ate.__main__ import main
        self.assertEqual(main(["validate"]), 0)


class TestWorkspace(unittest.TestCase):
    def test_read_only_restore(self):
        task = tasks.load_task(tasks.list_tasks()[0])
        with tempfile.TemporaryDirectory() as tmp:
            seed, sha = workspace.ensure_seed(task, tmp)
            wt = workspace.add_worktree(seed, sha, Path(tmp) / "wt", "run/test")
            before = workspace.snapshot_tree(wt)
            (wt / "new_file.py").write_text("x = 1\n")
            first = next(p for p in wt.rglob("*.py") if p.name != "new_file.py")
            first.write_text("# clobbered\n")
            self.assertNotEqual(workspace.snapshot_tree(wt), before)
            workspace.restore_tree(wt, before)
            self.assertEqual(workspace.snapshot_tree(wt), before)
            self.assertFalse((wt / "new_file.py").exists())
            workspace.remove_worktree(seed, wt)


class TestDryRunEndToEnd(unittest.TestCase):
    def _run(self, oracle):
        defaults = config.load_defaults()
        recs = []
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.jsonl"
            for cid in config.list_configs():
                task = tasks.load_task(tasks.list_tasks()[0])
                recs.append(pipeline.run_one(
                    task, config.load_config(cid), 1, defaults=defaults, sweep_id="test",
                    work_root=Path(tmp) / "work", results_path=out, binary=None,
                    claude_version="dry-run", harness_sha=None,
                    fake=pipeline.make_fake(task if oracle else None)))
            written = results.read([out])
        self.assertEqual(len(written), len(recs))
        for r in written:
            self.assertEqual(results.validate(r), [], r["run_id"])
        return recs

    def test_snapshot_fails(self):
        for r in self._run(oracle=False):
            self.assertEqual(r["status"], "failed", r["error"])
            self.assertEqual(r["cost_usd"], 0.0)

    def test_oracle_passes_and_pipeline_shape(self):
        recs = {r["config_id"]: r for r in self._run(oracle=True)}
        for r in recs.values():
            self.assertEqual(r["status"], "passed", r["error"])
            self.assertGreater(r["diff"]["files"], 0)
            self.assertEqual(r["read_only_violations"], [])
        self.assertEqual([s["name"] for s in recs["A"]["stages"]], ["solve"])
        self.assertEqual([s["name"] for s in recs["B"]["stages"]], ["build", "review", "fix"])
        self.assertEqual([s["name"] for s in recs["C"]["stages"]], ["plan", "build_1", "build_2", "review", "fix"])
        self.assertTrue(recs["B"]["fix_round"])

    def test_approve_skips_fix(self):
        defaults = config.load_defaults()
        task = tasks.load_task(tasks.list_tasks()[0])
        with tempfile.TemporaryDirectory() as tmp:
            r = pipeline.run_one(task, config.load_config("B"), 1, defaults=defaults, sweep_id="t",
                                 work_root=Path(tmp), results_path=Path(tmp) / "r.jsonl", binary=None,
                                 claude_version="dry-run", harness_sha=None,
                                 fake=pipeline.make_fake(task, verdict="APPROVE"))
        self.assertEqual([s["name"] for s in r["stages"]], ["build", "review"])
        self.assertFalse(r["fix_round"])


class TestReport(unittest.TestCase):
    def test_wilson(self):
        lo, hi = report.wilson(0, 3)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.4)
        lo, hi = report.wilson(10, 10)
        self.assertLess(lo, 1.0)
        self.assertEqual(hi, 1.0)

    def test_schema_rejects_bad_record(self):
        self.assertTrue(results.validate({"schema_version": 1}))


if __name__ == "__main__":
    unittest.main()
