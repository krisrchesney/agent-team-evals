"""Per-stage overrides (tools, allowed_tools, settings): they work, and they cannot break fairness or auth."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ate import REPO_ROOT, config, pipeline, tasks

GOLDEN = REPO_ROOT / "tests" / "golden_commands.json"


def dry_commands(cfg, tmp):
    task = tasks.load_task("t01-slugify")
    rec = pipeline.run_one(task, cfg, 1, defaults=config.load_defaults(), sweep_id="t", work_root=Path(tmp),
                           results_path=Path(tmp) / "r.jsonl", binary=None, claude_version="x",
                           harness_sha=None, fake=pipeline.make_fake(None))
    return {s["name"]: s["command"] for s in rec["stages"]}


def one_stage_config(**stage):
    st = {"name": "solve", "agent": None, "prompt": "solve.md", "mode": "write"}
    st.update(stage)
    return {"id": "X", "name": "x", "agents_dir": None, "stages": [st]}


class TestFairnessUnchanged(unittest.TestCase):
    def test_a_b_and_c_commands_are_byte_identical_to_the_golden_file(self):
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        for cid in ("A", "B", "C"):
            with tempfile.TemporaryDirectory() as tmp:
                got = dry_commands(config.load_config(cid), tmp)
            want = {s["stage"]: s["command"] for s in golden[cid]}
            self.assertEqual(got, want, f"config {cid} changed how it calls the CLI")

    def test_the_real_configs_still_load_and_have_no_overrides(self):
        for cid in config.list_configs():
            for st in config.load_config(cid)["stages"]:
                self.assertFalse({"tools", "allowed_tools", "settings"} & set(st), (cid, st["name"]))


class TestOverridesApply(unittest.TestCase):
    def test_tools_and_allowed_tools_replace_the_defaults_for_that_stage_only(self):
        cfg = {"id": "X", "name": "x", "agents_dir": None, "stages": [
            {"name": "solve", "agent": None, "prompt": "solve.md", "mode": "write",
             "tools": "Read,Edit,Agent", "allowed_tools": ["Read", "Edit", "Agent"]},
            {"name": "again", "agent": None, "prompt": "solve.md", "mode": "write"}]}
        with tempfile.TemporaryDirectory() as tmp:
            cmds = dry_commands(cfg, tmp)
        first, second = cmds["solve"], cmds["again"]
        self.assertEqual(first[first.index("--tools") + 1], "Read,Edit,Agent")
        self.assertEqual(first[first.index("--allowedTools") + 1], "Read,Edit,Agent")
        defaults = config.load_defaults()
        self.assertEqual(second[second.index("--tools") + 1], defaults["tools_write"])
        self.assertEqual(second[second.index("--allowedTools") + 1], ",".join(defaults["allowed_tools_write"]))

    def test_settings_file_is_passed_to_the_cli(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(config, "CONFIG_DIR", Path(tmp) / "configs"):
            fake_configs = Path(tmp) / "configs"
            shutil.copytree(REPO_ROOT / "configs", fake_configs)   # prompts and defaults, plus our settings file
            (fake_configs / "gate.json").write_text('{"hooks": {}}', encoding="utf-8")
            cfg = one_stage_config(settings="gate.json")
            config.validate_stage(cfg["stages"][0], "X")
            cmds = dry_commands(cfg, tmp)
        cmd = cmds["solve"]
        self.assertEqual(Path(cmd[cmd.index("--settings") + 1]).name, "gate.json")

    def test_no_override_means_no_settings_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotIn("--settings", dry_commands(one_stage_config(), tmp)["solve"])


class TestOverridesCannotWeakenSafety(unittest.TestCase):
    def test_safe_mode_and_strict_mcp_stay_on_and_bare_stays_off_even_with_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = dry_commands(one_stage_config(tools="Read", allowed_tools=["Read"]), tmp)["solve"]
        self.assertIn("--safe-mode", cmd)
        self.assertIn("--strict-mcp-config", cmd)
        self.assertNotIn("--bare", cmd)
        self.assertIn("--permission-prompts", cmd)

    def test_unknown_stage_keys_are_rejected(self):
        for key in ("bare", "model", "safe_mode", "env", "api_key", "permission_mode"):
            with self.assertRaises(ValueError, msg=key):
                config.validate_stage({"name": "s", "prompt": "solve.md", "mode": "write", key: "x"}, "X")

    def test_wrong_types_are_rejected(self):
        for bad in ({"tools": ["Read"]}, {"tools": ""}, {"allowed_tools": "Read"}, {"allowed_tools": []},
                    {"allowed_tools": [1]}, {"settings": 5}):
            with self.assertRaises(ValueError, msg=str(bad)):
                config.validate_stage({"name": "s", "prompt": "solve.md", "mode": "write", **bad}, "X")

    def test_settings_must_live_inside_configs(self):
        for bad in ("../README.md", "../../etc/passwd", "/etc/passwd", "C:/Windows/win.ini", "missing.json"):
            with self.assertRaises(ValueError, msg=bad):
                config.settings_path(bad)

    def test_settings_cannot_change_auth_model_or_permissions(self):
        forbidden = [{"apiKeyHelper": "echo key"}, {"model": "opus"}, {"forceLoginMethod": "console"},
                     {"env": {"ANTHROPIC_API_KEY": "x"}}, {"env": {"CLAUDE_CODE_USE_BEDROCK": "1"}},
                     {"env": {"AWS_BEARER_TOKEN_BEDROCK": "x"}},
                     {"permissions": {"defaultMode": "bypassPermissions"}},
                     {"mcpServers": {"x": {}}}, {"enabledPlugins": {"x": True}}]
        for body in forbidden:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "s.json"
                path.write_text(json.dumps(body), encoding="utf-8")
                with self.assertRaises(ValueError, msg=str(body)):
                    config.check_settings_file(path)

    def test_a_harmless_settings_file_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            path.write_text(json.dumps({"hooks": {"Stop": []}, "env": {"MY_FLAG": "1"}}), encoding="utf-8")
            config.check_settings_file(path)


if __name__ == "__main__":
    unittest.main()
