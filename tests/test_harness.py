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


class TestSubscriptionSafety(unittest.TestCase):
    """The "no extra $" guarantees for subscription mode."""

    def test_child_env_strips_every_credential_and_parent_session_var(self):
        defaults = {"auth": "subscription", "claude_config_dir": "D:/ate-work/claude-config"}
        base = {"ANTHROPIC_API_KEY": "k", "ANTHROPIC_AUTH_TOKEN": "t", "ANTHROPIC_BASE_URL": "http://x",
                "CLAUDE_CODE_OAUTH_TOKEN": "o", "CLAUDE_CODE_SIMPLE": "1", "CLAUDE_CODE_USE_BEDROCK": "1",
                "AWS_BEARER_TOKEN_BEDROCK": "b", "CLAUDECODE": "1", "PATH": "/bin", "anthropic_api_key": "lower"}
        env = claude.child_env(defaults, base=base)
        self.assertEqual(env["PATH"], "/bin")
        self.assertEqual(Path(env["CLAUDE_CONFIG_DIR"]), Path("D:/ate-work/claude-config"))
        leftover = {k for k in env if k not in ("PATH", "CLAUDE_CONFIG_DIR")}
        self.assertEqual(leftover, set())

    def test_defaults_use_subscription(self):
        d = config.load_defaults()
        self.assertEqual(d["auth"], "subscription")
        self.assertTrue(d["claude_config_dir"])

    def test_subscription_stage_has_no_bare_flag(self):
        spec = claude.StageSpec(name="s", prompt="p", cwd=Path("."), log_path=Path("x"), model="sonnet",
                                max_turns=5, budget_usd=1.0, timeout_s=10, permission_mode="acceptEdits",
                                tools="Read", allowed_tools=["Read"], bare=False)
        self.assertNotIn("--bare", claude.build_command("claude", spec))

    def _log(self, tmp, events):
        log = Path(tmp) / "s.jsonl"
        log.write_text("\n".join(json.dumps(e) for e in events) + "\n")
        return log

    def test_scan_log_detects_rate_limit_and_key_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp, [
                {"type": "system", "subtype": "init", "apiKeySource": "none"},
                {"type": "system", "subtype": "api_retry", "error": "rate_limit", "attempt": 1},
                {"type": "result", "subtype": "error_during_execution", "is_error": True,
                 "result": "Claude usage limit reached. Your limit will reset at 5pm"}])
            scan = claude.scan_log(log)
        self.assertTrue(scan["rate_limited"])
        self.assertEqual(scan["api_key_source"], "none")

    def test_normal_reply_is_not_a_rate_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = self._log(tmp, [{"type": "result", "subtype": "success", "is_error": False,
                                   "result": "Added a rate limit test."}])
            self.assertFalse(claude.scan_log(log)["rate_limited"])

    def _run_with(self, events_fn):
        defaults = config.load_defaults()
        task = tasks.load_task(tasks.list_tasks()[0])
        with tempfile.TemporaryDirectory() as tmp:
            # A non-None `fake` normally disables the auth check, so mimic a real run's log instead.
            def fake(spec):
                return events_fn(spec)
            rec = pipeline.run_one(task, config.load_config("B"), 1, defaults=defaults, sweep_id="t",
                                   work_root=Path(tmp), results_path=Path(tmp) / "r.jsonl", binary=None,
                                   claude_version="x", harness_sha=None, fake=fake)
        return rec

    def test_rate_limit_stops_run_and_is_retryable(self):
        rec = self._run_with(lambda spec: [
            {"type": "system", "subtype": "init", "apiKeySource": "none"},
            {"type": "result", "subtype": "error_during_execution", "is_error": True,
             "result": "You've hit your usage limit", "total_cost_usd": 0.01, "usage": {}}])
        self.assertEqual(rec["status"], "rate_limited")
        self.assertEqual(len(rec["stages"]), 1)
        self.assertIn("rate_limited", pipeline.RETRYABLE)

    def test_personal_claude_md_canary(self):
        rec = self._run_with(lambda spec: [
            {"type": "system", "subtype": "init", "apiKeySource": "none", "plugins": [{"name": "data"}]},
            {"type": "result", "subtype": "success", "is_error": False, "num_turns": 1,
             "result": "2026-10-29 09:00 CST\nDone.", "total_cost_usd": 0.0, "usage": {}}])
        self.assertTrue(any("CLAUDE.md" in f for f in rec["isolation_flags"]))
        self.assertTrue(any("plugins" in f for f in rec["isolation_flags"]))

    def test_paid_run_refuses_without_signed_in_profile(self):
        from ate.__main__ import main
        with tempfile.TemporaryDirectory() as tmp:
            # An empty config dir is never signed in, so the run must refuse before any stage starts.
            import ate.config as cfgmod
            orig = cfgmod.load_defaults
            cfgmod.load_defaults = lambda path=None: dict(orig(path), claude_config_dir=str(Path(tmp) / "empty"))
            try:
                code = main(["run", "--tasks", "t01", "--configs", "A", "--reps", "1",
                             "--max-total-usd", "0.5", "--yes", "--results-dir", tmp,
                             "--work-root", str(Path(tmp) / "w")])
            finally:
                cfgmod.load_defaults = orig
            self.assertEqual(code, 2)
            self.assertEqual(list(Path(tmp).glob("*.jsonl")), [])


class TestResume(unittest.TestCase):
    def test_resume_reruns_only_retryable(self):
        from ate.__main__ import main
        with tempfile.TemporaryDirectory() as tmp:
            args = ["run", "--dry-run", "--oracle", "--tasks", "t01", "--configs", "A,B", "--reps", "1",
                    "--results-dir", tmp, "--work-root", str(Path(tmp) / "w")]
            self.assertEqual(main(args), 0)
            path = next(Path(tmp).glob("*.jsonl"))
            recs = results.read([path])
            recs[1]["status"] = "rate_limited"  # pretend B hit the limit
            path.write_text("".join(json.dumps(r) + "\n" for r in recs))
            self.assertEqual(main(args + ["--resume", path.stem]), 0)
            after = results.read([path])
        self.assertEqual(len(after), 3)
        self.assertEqual(after[-1]["config_id"], recs[1]["config_id"])
        self.assertEqual(after[-1]["attempt"], 2)
        self.assertEqual(after[-1]["status"], "passed")
        self.assertEqual(len(report.counted(after)), 2)


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
