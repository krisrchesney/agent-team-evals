"""The ask_user stand-in user (T-23): the MCP server, its answer matching and log, and the pipeline wiring."""
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ate import REPO_ROOT, askuser, claude, config, pipeline, results, tasks
from ate.askuser import server

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "askuser_task"
SHEET = {"default": "No preference; use your judgment.", "answers": [
    {"id": "currency", "keywords": ["currency", "euro"], "answer": "USD only."},
    {"id": "rounding", "keywords": ["round", "cents"], "answer": "Whole cents."},
    {"id": "id", "keywords": ["id"], "answer": "Use the id."},
]}


def rpc(method, params=None, mid=1):
    msg = {"jsonrpc": "2.0", "method": method}
    if mid is not None:
        msg["id"] = mid
    if params is not None:
        msg["params"] = params
    return msg


def ask(question, mid=2):
    return rpc("tools/call", {"name": "ask_user", "arguments": {"question": question}}, mid)


class TestProtocol(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "q.jsonl"
        self.srv = server.Server(json.loads(json.dumps(SHEET)), self.log)

    def test_initialize_echoes_the_clients_protocol_version_and_offers_tools(self):
        r = self.srv.handle(rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}}))
        self.assertEqual(r["id"], 1)
        self.assertEqual(r["result"]["protocolVersion"], "2025-03-26")
        self.assertIn("tools", r["result"]["capabilities"])
        self.assertEqual(r["result"]["serverInfo"]["name"], "ask_user")

    def test_notifications_get_no_reply(self):
        self.assertIsNone(self.srv.handle(rpc("notifications/initialized", mid=None)))

    def test_tools_list_has_one_tool_with_a_required_question(self):
        tools = self.srv.handle(rpc("tools/list"))["result"]["tools"]
        self.assertEqual([t["name"] for t in tools], ["ask_user"])
        self.assertEqual(tools[0]["inputSchema"]["required"], ["question"])

    def test_tools_call_answers_by_keyword(self):
        r = self.srv.handle(ask("Which currency should totals use?"))["result"]
        self.assertEqual(r["content"], [{"type": "text", "text": "On currency: USD only."}])
        self.assertFalse(r["isError"])

    def test_no_keyword_gives_the_default_answer(self):
        r = self.srv.handle(ask("What colour should the logo be?"))["result"]
        self.assertEqual(r["content"][0]["text"], "No preference; use your judgment.")

    def test_unknown_method_and_unknown_tool_are_errors(self):
        self.assertEqual(self.srv.handle(rpc("resources/list"))["error"]["code"], -32601)
        bad = self.srv.handle(rpc("tools/call", {"name": "other", "arguments": {}}))
        self.assertIn("error", bad)
        self.assertEqual(self.srv.handle(rpc("ping"))["result"], {})

    def test_empty_question_is_a_tool_error_and_not_logged(self):
        for args in ({}, {"question": "  "}, {"question": 5}):
            r = self.srv.handle(rpc("tools/call", {"name": "ask_user", "arguments": args}))["result"]
            self.assertTrue(r["isError"])
        self.assertFalse(self.log.exists())

    def test_every_question_is_logged_with_its_answer_and_matched_entry(self):
        self.srv.handle(ask("Round to cents?"))
        self.srv.handle(ask("Anything else?"))
        self.srv.handle(ask("Which currency, and how do you round?"))
        lines = [json.loads(x) for x in self.log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([(x["question"], x["answer"], x["matched"]) for x in lines],
                         [("Round to cents?", "On rounding: Whole cents.", ["rounding"]),
                          ("Anything else?", "No preference; use your judgment.", []),
                          ("Which currency, and how do you round?", "On currency: USD only.\n\nOn rounding: Whole cents.",
                           ["currency", "rounding"])])
        self.assertEqual([q["matched"] for q in askuser.read_log(self.log)],
                         [["rounding"], [], ["currency", "rounding"]])
        self.assertEqual(len(askuser.read_log(self.log, skip=1)), 2)

    def test_compound_question_gets_every_answer_in_sheet_order(self):
        r = self.srv.handle(ask("How do you round, and which currency?"))["result"]
        self.assertEqual(r["content"][0]["text"], "On currency: USD only.\n\nOn rounding: Whole cents.")

    def test_tool_text_allows_several_questions_in_one_call(self):
        self.assertNotIn("one question", server.TOOL["description"].lower())
        self.assertIn("several", server.TOOL["description"])
        self.assertIn("several", server.TOOL["inputSchema"]["properties"]["question"]["description"])

    def test_serve_loop_reads_lines_and_survives_garbage(self):
        stdin = io.StringIO("\n".join([json.dumps(rpc("tools/list")), "not json", "[1]",
                                       json.dumps(rpc("notifications/initialized", mid=None))]) + "\n")
        out = io.StringIO()
        server.serve(self.srv, stdin, out)
        replies = [json.loads(x) for x in out.getvalue().splitlines()]
        self.assertEqual([r.get("id") for r in replies], [1, None, None])
        self.assertEqual([r.get("error", {}).get("code") for r in replies[1:]], [-32700, -32600])


class TestMatching(unittest.TestCase):
    def match(self, q):
        return server.match_answer(SHEET, q)

    def test_case_insensitive(self):
        self.assertEqual(self.match("EURO or dollars?")[1], ["currency"])

    def test_keywords_match_at_the_start_of_a_word_only(self):
        self.assertEqual(self.match("Which side?")[1], [])  # "id" is not inside "side"
        self.assertEqual(self.match("Is there an id column?")[1], ["id"])
        self.assertEqual(self.match("Rounded how?")[1], ["rounding"])  # "round" starts "rounded"

    def test_every_matching_entry_answers_in_sheet_order(self):
        self.assertEqual(self.match("Round to cents in euro?")[1], ["currency", "rounding"])
        self.assertEqual(self.match("Round it, and is there an id?")[1], ["rounding", "id"])
        self.assertEqual(self.match("Nothing relevant")[0], "No preference; use your judgment.")

    def test_multi_word_keyword(self):
        sheet = {"default": "d", "answers": [{"id": "x", "keywords": ["time  zone"], "answer": "UTC"}]}
        self.assertEqual(server.match_answer(sheet, "Which Time Zone?"), ("On x: UTC", ["x"]))
        self.assertEqual(server.match_answer(sheet, "Which zone, time-wise?"), ("d", []))


class TestAnswerSheet(unittest.TestCase):
    def write(self, tmp, data):
        p = Path(tmp) / "a.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def test_fixture_sheet_loads_and_gets_the_standard_default(self):
        sheet = askuser.load_answers(FIXTURE / "answers.json")
        self.assertEqual(sheet["default"], askuser.DEFAULT_ANSWER)
        self.assertEqual(askuser.DEFAULT_ANSWER, "No preference; use your judgment.")

    def test_bad_sheets_are_rejected(self):
        bad = [[], {}, {"answers": [{"answer": "x"}]}, {"answers": [{"keywords": [], "answer": "x"}]},
               {"answers": [{"keywords": ["a"], "answer": ""}]}, {"answers": [{"keywords": [3], "answer": "x"}]},
               {"answers": [{"id": "a", "keywords": ["a"], "answer": "x"}, {"id": "a", "keywords": ["b"], "answer": "y"}]},
               {"answers": [], "default": ""}]
        with tempfile.TemporaryDirectory() as tmp:
            for data in bad:
                with self.assertRaises(ValueError, msg=data):
                    server.load_answers(self.write(tmp, data))
            self.assertEqual(server.load_answers(self.write(tmp, {"answers": []}))["default"], askuser.DEFAULT_ANSWER)


class TestStdioProcess(unittest.TestCase):
    """The real thing: start the server as the harness will and talk to it over pipes."""

    def test_round_trip_over_stdio_from_the_written_mcp_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "q.jsonl"
            cfg = askuser.write_mcp_config(Path(tmp) / "mcp.json", FIXTURE / "answers.json", log, "Your call.")
            spec = json.loads(cfg.read_text(encoding="utf-8"))["mcpServers"]["ask_user"]
            msgs = [rpc("initialize", {"protocolVersion": "2024-11-05"}), rpc("notifications/initialized", mid=None),
                    rpc("tools/list", mid=2), ask("What greeting do you want?", mid=3), ask("Colour?", mid=4)]
            proc = subprocess.run([spec["command"], *spec["args"]], input="\n".join(map(json.dumps, msgs)) + "\n",
                                  capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn("\r", proc.stdout)
            replies = {r["id"]: r for r in map(json.loads, proc.stdout.splitlines())}
            self.assertEqual(sorted(replies), [1, 2, 3, 4])
            self.assertEqual(replies[3]["result"]["content"][0]["text"], 'On greeting: Say "Hello, <name>!".')
            self.assertEqual(replies[4]["result"]["content"][0]["text"], "Your call.")  # --default override
            self.assertEqual(len(askuser.read_log(log)), 2)

    def test_missing_answers_file_exits_nonzero(self):
        proc = subprocess.run([sys.executable, str(askuser.SERVER_FILE), "--answers", "nope.json"],
                              input="", capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 2)


class TestIsolationCheck(unittest.TestCase):
    def test_only_a_connected_ask_user_server_is_acceptable(self):
        self.assertEqual(askuser.isolation_problems([{"name": "ask_user", "status": "connected"}]), [])
        self.assertEqual(askuser.isolation_problems([{"name": "ask_user"}]), [])

    def test_other_servers_failures_and_absence_are_flagged(self):
        self.assertEqual(len(askuser.isolation_problems([{"name": "ask_user", "status": "connected"},
                                                         {"name": "claude.ai Gmail", "status": "connected"}])), 1)
        self.assertEqual(len(askuser.isolation_problems([{"name": "ask_user", "status": "failed"}])), 1)
        self.assertEqual(len(askuser.isolation_problems([])), 1)
        self.assertEqual(len(askuser.isolation_problems(None)), 1)

    def test_skills_and_slash_commands_are_flagged(self):
        ok = [{"name": "ask_user", "status": "connected"}]
        self.assertEqual(askuser.isolation_problems(ok, [], []), [])
        self.assertEqual(len(askuser.isolation_problems(ok, ["deploy"], [])), 1)
        self.assertEqual(len(askuser.isolation_problems(ok, ["x"], ["/init"])), 2)


def _spec(**kw):
    base = dict(name="s", prompt="p", cwd=Path("."), log_path=Path("x"), model="sonnet", max_turns=5,
                cap_api_equiv_usd=1.0, timeout_s=10, permission_mode="acceptEdits", tools="Read",
                allowed_tools=["Read"], bare=False)
    base.update(kw)
    return claude.StageSpec(**base)


class TestCommand(unittest.TestCase):
    def test_mcp_config_goes_alongside_strict_mcp_config(self):
        cmd = claude.build_command("claude", _spec(mcp_config=Path("m.json"), safe_mode=True))
        self.assertIn("--strict-mcp-config", cmd)
        self.assertEqual(cmd[cmd.index("--mcp-config") + 1], "m.json")

    def test_ask_user_runs_drop_safe_mode_for_empty_setting_sources_and_no_slash_commands(self):
        cmd = claude.build_command("claude", _spec(mcp_config=Path("m.json"), safe_mode=True))
        self.assertNotIn("--safe-mode", cmd)
        self.assertEqual(cmd[cmd.index("--setting-sources") + 1], "")
        self.assertIn("--disable-slash-commands", cmd)

    def test_normal_subscription_runs_keep_safe_mode(self):
        cmd = claude.build_command("claude", _spec(safe_mode=True))
        self.assertIn("--safe-mode", cmd)
        self.assertNotIn("--setting-sources", cmd)
        self.assertNotIn("--disable-slash-commands", cmd)

    def test_without_the_option_the_command_has_no_mcp_config(self):
        self.assertNotIn("--mcp-config", claude.build_command("claude", _spec()))

    def test_logged_command_hides_the_config_path(self):
        cmd = claude._redact(claude.build_command("claude", _spec(mcp_config=Path(r"C:\Users\someone\mcp.json"))))
        self.assertNotIn("someone", " ".join(cmd))


class TestPipelineDryRun(unittest.TestCase):
    def task(self):
        return tasks.Task("askuser-fixture", FIXTURE,
                          json.loads((FIXTURE / "task.json").read_text(encoding="utf-8")))

    def run_it(self, cid, questions, oracle=True):
        """Dry run in which each write stage 'calls' the real server with `questions`, as the agent would."""
        task = self.task()
        inner = pipeline.make_fake(task if oracle else None)

        def fake(spec):
            self.assertIsNotNone(spec.mcp_config)
            self.assertIn(askuser.ALLOWED_TOOL, spec.allowed_tools)
            if "Edit" in spec.tools:
                cfg = json.loads(Path(spec.mcp_config).read_text(encoding="utf-8"))["mcpServers"]["ask_user"]
                msgs = [rpc("initialize", {}), ask(questions[0], mid=2)] + [ask(q, mid=3 + i) for i, q in enumerate(questions[1:])]
                p = subprocess.run([cfg["command"], *cfg["args"]], input="\n".join(map(json.dumps, msgs)) + "\n",
                                   capture_output=True, text=True, encoding="utf-8", timeout=60)
                self.assertEqual(p.returncode, 0, p.stderr)
            return inner(spec)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.jsonl"
            rec = pipeline.run_one(task, config.load_config(cid), 1, defaults=config.load_defaults(), sweep_id="t",
                                   work_root=Path(tmp) / "w", results_path=out, binary=None, claude_version="dry-run",
                                   harness_sha=None, fake=fake)
            written = results.read([out])
        self.assertEqual(results.validate(written[0]), [])
        return rec

    def test_questions_are_recorded_with_count_stage_and_matched_entry(self):
        rec = self.run_it("A", ["Which greeting?", "Any colour?"])
        self.assertEqual(rec["status"], "passed", rec["error"])
        self.assertEqual(rec["questions_asked"], 2)
        self.assertEqual([(q["stage"], q["matched"]) for q in rec["questions"]], [("solve", ["greeting"]), ("solve", [])])
        self.assertEqual(rec["questions"][1]["answer"], "No preference; use your judgment.")
        self.assertEqual(rec["topics_covered"], ["greeting"])
        self.assertEqual(rec["isolation_flags"], [])
        cmd = rec["stages"][0]["command"]
        self.assertIn("--strict-mcp-config", cmd)
        self.assertIn("--mcp-config", cmd)
        self.assertIn(askuser.ALLOWED_TOOL, cmd[cmd.index("--allowedTools") + 1].split(","))

    def test_questions_from_every_stage_are_kept_apart_and_counted_once(self):
        rec = self.run_it("B", ["Which language?"], oracle=False)
        stages = [q["stage"] for q in rec["questions"]]
        self.assertEqual(stages, [s["name"] for s in rec["stages"] if s["name"] in ("build", "fix")])
        self.assertEqual(rec["questions_asked"], len(stages))

    def test_topics_covered_are_distinct_across_stages_and_in_sheet_order(self):
        rec = self.run_it("B", ["Which language?", "And the greeting?"], oracle=False)
        self.assertGreater(len({q["stage"] for q in rec["questions"]}), 1)
        self.assertEqual(rec["topics_covered"], ["greeting", "language"])  # sheet order, each once

    def test_no_questions_is_zero_not_missing(self):
        task = self.task()
        with tempfile.TemporaryDirectory() as tmp:
            rec = pipeline.run_one(task, config.load_config("A"), 1, defaults=config.load_defaults(), sweep_id="t",
                                   work_root=Path(tmp), results_path=Path(tmp) / "r.jsonl", binary=None,
                                   claude_version="dry-run", harness_sha=None, fake=pipeline.make_fake(task))
        self.assertEqual((rec["questions_asked"], rec["questions"], rec["topics_covered"]), (0, [], []))

    def test_tasks_without_the_option_are_unchanged(self):
        task = tasks.load_task("t01-slugify")
        self.assertFalse(task.ask_user)
        with tempfile.TemporaryDirectory() as tmp:
            rec = pipeline.run_one(task, config.load_config("A"), 1, defaults=config.load_defaults(), sweep_id="t",
                                   work_root=Path(tmp), results_path=Path(tmp) / "r.jsonl", binary=None,
                                   claude_version="dry-run", harness_sha=None, fake=pipeline.make_fake(task))
        self.assertNotIn("questions_asked", rec)
        self.assertNotIn("--mcp-config", rec["stages"][0]["command"])

    def prompts(self, task, cid):
        seen = []
        inner = pipeline.make_fake(task)

        def fake(spec):
            seen.append(spec.prompt)
            return inner(spec)
        with tempfile.TemporaryDirectory() as tmp:
            pipeline.run_one(task, config.load_config(cid), 1, defaults=config.load_defaults(), sweep_id="t",
                             work_root=Path(tmp), results_path=Path(tmp) / "r.jsonl", binary=None,
                             claude_version="dry-run", harness_sha=None, fake=fake)
        return seen

    def test_ask_user_prompts_say_to_ask_not_that_nobody_will_answer(self):
        for cid in ("A", "AS", "D"):
            for p in self.prompts(self.task(), cid):
                self.assertNotIn("nobody will answer", p)
                self.assertNotIn("$questions_rule", p)
            self.assertIn("ask_user tool", self.prompts(self.task(), cid)[0])

    def test_other_tasks_keep_the_original_no_questions_wording(self):
        p = self.prompts(tasks.load_task("t01-slugify"), "A")[0]
        self.assertIn("- Do not ask questions; nobody will answer. Make a reasonable choice", p)
        self.assertNotIn("ask_user", p)

    def test_broken_answer_sheet_is_a_harness_error_before_any_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "task"
            shutil.copytree(FIXTURE, root)
            (root / "answers.json").write_text("{}", encoding="utf-8")
            task = tasks.Task("askuser-fixture", root, json.loads((root / "task.json").read_text(encoding="utf-8")))
            rec = pipeline.run_one(task, config.load_config("A"), 1, defaults=config.load_defaults(), sweep_id="t",
                                   work_root=Path(tmp) / "w", results_path=Path(tmp) / "r.jsonl", binary=None,
                                   claude_version="dry-run", harness_sha=None, fake=pipeline.make_fake(None))
        self.assertEqual(rec["status"], "harness_error")
        self.assertEqual(rec["stages"], [])


if __name__ == "__main__":
    unittest.main()
