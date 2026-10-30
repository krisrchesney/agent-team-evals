"""Run one (task, config, repetition): worktree -> stages -> hidden tests -> one result record.

The harness, not the model, decides the control flow: which stage runs next, whether the fix
round happens, how many builder runs a plan gets. That keeps B and C exactly as specified
("one round of fixes") and lets us charge every token to a named stage.
"""
import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from string import Template

from . import SCHEMA_VERSION, claude, config, grade, results, workspace

MIN_STAGE_BUDGET = 0.05  # below this, starting another stage is pointless
# Statuses that say "this run tells us nothing about the config": re-run them with --resume,
# and leave them out of every statistic.
RETRYABLE = ("rate_limited", "auth_error", "harness_error")
# The user's personal CLAUDE.md makes every reply start with a CST timestamp. If a benchmark
# answer starts that way, the clean profile isn't clean.
_PERSONAL_CANARY = re.compile(r"^\s*\d{4}-\d{2}-\d{2} \d{1,2}:\d{2} CST")


def _role_prompt(agents, name):
    """The role's system prompt from its .claude/agents file (None when the stage has no role)."""
    if not name:
        return None
    if name not in agents:
        raise KeyError(f"stage names role {name!r} but the config's agents are {sorted(agents)}")
    return agents[name]["prompt"]


def _render(template_name, **values):
    return Template(config.load_prompt(template_name)).safe_substitute(
        {k: ("" if v is None else str(v)) for k, v in values.items()})


def _format_findings(structured):
    findings = (structured or {}).get("findings") or []
    if not findings:
        return "(none given)"
    lines = []
    for i, f in enumerate(findings, 1):
        bits = [f.get("problem", "")]
        if f.get("requirement"):
            bits.insert(0, f"[req {f['requirement']}]")
        if f.get("file"):
            bits.append(f"(file: {f['file']})")
        if f.get("failing_input"):
            bits.append(f"failing input: {f['failing_input']}")
        lines.append(f"{i}. " + " ".join(b for b in bits if b))
    return "\n".join(lines)


def _expand_stages(cfg, outputs):
    """Yield (stage_def, extra_template_values) lazily, so later stages can read earlier outputs."""
    for st in cfg["stages"]:
        cond = st.get("only_if")
        if cond:
            src = outputs.get(cond["stage"]) or {}
            if src.get(cond["field"]) != cond["equals"]:
                continue
        if "foreach" in st:
            src = outputs.get(st["foreach"]["stage"]) or {}
            items = (src.get(st["foreach"]["field"]) or [])[: cfg.get("max_subtasks", 3)]
            risks = "\n".join(f"- {r}" for r in src.get("risks") or []) or "(none listed)"
            for i, item in enumerate(items, 1):
                yield dict(st, name=f"{st['name']}_{i}"), {
                    "subtask_index": i, "subtask_count": len(items), "risks": risks,
                    "subtask_title": item.get("title"),
                    "subtask_requirements": ", ".join(map(str, item.get("requirements") or [])) or "see instructions",
                    "subtask_files": ", ".join(item.get("files") or []) or "as needed",
                    "subtask_instructions": item.get("instructions"),
                    "subtask_done_when": item.get("done_when"),
                }
        else:
            yield st, {}


def run_one(task, cfg, rep, *, defaults, sweep_id, work_root, results_path, binary,
            claude_version, harness_sha, fake=None, keep_worktree=True, attempt=1):
    started = datetime.now(timezone.utc)
    run_id = f"{sweep_id}/{task.id}/{cfg['id']}/r{rep}"
    suffix = "" if attempt == 1 else f"__a{attempt}"
    run_dir = Path(work_root) / "sweeps" / sweep_id / f"{task.id}__{cfg['id']}__r{rep}{suffix}"
    wt_path = run_dir / "wt"
    subscription = defaults.get("auth", "subscription") == "subscription"
    env = claude.child_env(defaults) if fake is None else None
    budget = float(defaults["run_cap_api_equiv_usd"])
    rec = {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "sweep_id": sweep_id,
        "started_utc": started.isoformat(timespec="seconds"), "task_id": task.id,
        "config_id": cfg["id"], "rep": rep, "model": defaults["model"], "dry_run": fake is not None,
        "status": "harness_error", "passed": False,
        "tests": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
        "api_equiv_usd": 0.0, "tokens": {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0},
        "agent_wall_s": 0.0, "num_turns": 0, "stages": [], "review_verdict": None,
        "fix_round": False, "plan_subtasks": None,
        "diff": {"files": 0, "insertions": 0, "deletions": 0}, "touched_tests": False,
        "read_only_violations": [], "leak_suspected": [], "claude_version": claude_version,
        "harness_sha": harness_sha, "cap_api_equiv_usd": budget, "worktree": str(wt_path), "error": None,
        "auth": defaults.get("auth", "subscription"), "attempt": attempt, "isolation_flags": [],
    }
    seed = None
    try:
        seed, seed_sha = workspace.ensure_seed(task, work_root)
        branch = f"run/{sweep_id}/{cfg['id']}/r{rep}{suffix.replace('__', '-')}"
        workspace.add_worktree(seed, seed_sha, wt_path, branch)

        agents = config.load_agents(cfg.get("agents_dir"))
        config.check_agent_models(agents, defaults["model"])
        agents_file = None
        if agents:
            agents_file = run_dir / "agents.json"
            agents_file.write_text(json.dumps(agents, indent=2), encoding="utf-8")

        outputs, last_summary, stopped = {}, "", None
        leak_needles = ["hidden_tests", "_ate_hidden", "agent-team-evals"]
        for st, extra in _expand_stages(cfg, outputs):
            remaining = budget - rec["api_equiv_usd"]
            if remaining < MIN_STAGE_BUDGET:
                stopped = "cap_exceeded"
                break
            read_only = st.get("mode") == "read"
            prompt = _render(st["prompt"], task_prompt=task.prompt, builder_summary=last_summary or "(none)",
                             findings=_format_findings(outputs.get("review")), **extra)
            spec = claude.StageSpec(
                name=st["name"], prompt=prompt, cwd=wt_path, log_path=run_dir / f"{st['name']}.jsonl",
                model=defaults["model"], max_turns=int(defaults["stage_max_turns"]),
                cap_api_equiv_usd=remaining, timeout_s=int(defaults["stage_timeout_s"]),
                permission_mode=defaults["permission_mode"],
                tools=st.get("tools") or defaults["tools_read" if read_only else "tools_write"],
                allowed_tools=st.get("allowed_tools") or defaults["allowed_tools_read" if read_only else "allowed_tools_write"],
                settings_file=config.settings_path(st["settings"]) if st.get("settings") else None,
                bare=not subscription, safe_mode=subscription, effort=defaults.get("effort"), env=env,
                agent=st.get("agent"), agents_file=agents_file if st.get("agent") and not subscription else None,
                role_prompt=_role_prompt(agents, st.get("agent")) if subscription else None,
                json_schema=config.load_schema(st["schema"]) if st.get("schema") else None,
            )
            before = workspace.snapshot_tree(wt_path) if read_only else None
            res = claude.run_stage(binary, spec, fake=fake)
            if read_only and workspace.snapshot_tree(wt_path) != before:
                rec["read_only_violations"].append(st["name"])
                workspace.restore_tree(wt_path, before)

            rec["stages"].append(res.as_record())
            rec["api_equiv_usd"] = round(rec["api_equiv_usd"] + res.api_equiv_usd, 6)
            for k in rec["tokens"]:
                rec["tokens"][k] += res.tokens.get(k, 0)
            rec["num_turns"] += res.num_turns
            rec["agent_wall_s"] = round(rec["agent_wall_s"] + res.duration_s, 2)
            rec["leak_suspected"] += [f"{st['name']}:{n}" for n in claude.log_mentions(spec.log_path, leak_needles)]

            base = st["name"].split("_")[0] if "foreach" in st else st["name"]
            if res.structured is not None:
                outputs[base] = res.structured
            if not read_only:
                last_summary = res.result_text[:4000]
            if base == "review":
                rec["review_verdict"] = (res.structured or {}).get("verdict")
            if base == "plan":
                rec["plan_subtasks"] = len((res.structured or {}).get("subtasks") or [])
            if base == "fix":
                rec["fix_round"] = True

            if subscription and fake is None and res.api_key_source not in (None, "none"):
                stopped = "auth_error"
                rec["error"] = f"stage {st['name']} authenticated with {res.api_key_source}, not the subscription"
                break
            if _PERSONAL_CANARY.match(res.result_text or ""):
                rec["isolation_flags"].append(f"{st['name']}:personal CLAUDE.md rule visible in reply")
            init = claude.scan_log(spec.log_path)["init"] or {}
            extra_plugins = [pl for pl in init.get("plugins") or [] if pl.get("path") != "builtin"]
            if extra_plugins:
                rec["isolation_flags"].append(f"{st['name']}:plugins loaded: {extra_plugins}")
            if init.get("mcp_servers"):
                rec["isolation_flags"].append(f"{st['name']}:mcp_servers loaded: {init['mcp_servers']}")
            tools = init.get("tools")
            if (fake is None and tools is not None and not read_only
                    and not {"Bash", "PowerShell"} & set(tools)):
                stopped = "harness_error"
                rec["error"] = (f"stage {st['name']} had no shell tool (tools: {sorted(tools)}), "
                                f"so the agent could not run tests")
                break
            if res.rate_limited:
                stopped = "rate_limited"
                rec["error"] = (res.error or res.result_text or "usage limit")[:500]
                break
            if res.timed_out:
                stopped = "timeout"
                break
            if res.subtype and "budget" in res.subtype:
                stopped = "cap_exceeded"
                break
            # A failed write stage or planner ends the run. A failed reviewer does not: there is
            # simply no verdict, so the fix round is skipped and we grade what the builder made.
            if (res.exit_code != 0 or res.subtype is None) and (base == "plan" or not read_only):
                # The CLI rejected the command before any model call (0 tokens, 0 turns): a harness problem,
                # not a verdict on the config, so it is retryable and left out of the statistics.
                never_ran = res.num_turns == 0 and sum(res.tokens.values()) == 0 and not res.timed_out
                stopped = "harness_error" if never_ran else "agent_error"
                rec["error"] = res.error
                break

        final_tree = workspace.snapshot_tree(wt_path)
        rec["diff"] = workspace.diff_stats(wt_path, seed_sha, final_tree)
        rec["touched_tests"] = any(p.startswith("tests/") for p in workspace.changed_paths(wt_path, seed_sha, final_tree))

        t = grade.grade(task, wt_path)
        rec["tests"] = {k: t[k] for k in ("total", "passed", "failed", "errors")}
        rec["passed"] = bool(t["ok"])
        if stopped in RETRYABLE:
            rec["status"] = stopped  # graded for the record, but not a verdict on the config
        else:
            rec["status"] = "passed" if rec["passed"] else (stopped or "failed")
        (run_dir / "hidden_tests.txt").write_text(t["output_tail"], encoding="utf-8")
    except Exception as exc:  # record the failure instead of killing the whole sweep
        rec["status"] = "harness_error"
        rec["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if seed is not None and not keep_worktree and wt_path.exists():
            workspace.remove_worktree(seed, wt_path)
    results.append(results_path, rec)
    return rec


def make_fake(task=None, verdict="CHANGES_NEEDED"):
    """Dry-run CLI. With `task` (oracle mode) write stages copy the reference solution in,
    so the dry run also exercises the pass path, diff stats and grading."""
    def fake(spec):
        if task is not None and "Edit" in spec.tools:
            shutil.copytree(task.solution, spec.cwd, dirs_exist_ok=True)
        return fake_claude(spec, verdict=verdict)
    return fake


def fake_claude(spec, verdict="CHANGES_NEEDED"):
    """Dry-run stand-in for the CLI: canned events, zero cost, exercises every pipeline branch."""
    structured = None
    if spec.json_schema and "verdict" in spec.json_schema.get("properties", {}):
        structured = {"verdict": verdict, "findings": [] if verdict == "APPROVE" else
                      [{"requirement": "1", "problem": "dry-run finding", "file": "n/a"}]}
    elif spec.json_schema and "subtasks" in spec.json_schema.get("properties", {}):
        structured = {"subtasks": [
            {"title": "first half", "requirements": ["1"], "files": [], "instructions": "dry run", "done_when": "n/a"},
            {"title": "second half", "requirements": ["2"], "files": [], "instructions": "dry run", "done_when": "n/a"}],
            "risks": ["dry run"]}
    time.sleep(0.01)
    return [
        {"type": "system", "subtype": "init", "dry_run": True, "agent": spec.agent, "model": spec.model},
        {"type": "result", "subtype": "success", "is_error": False, "duration_ms": 10,
         "duration_api_ms": 0, "num_turns": 1, "result": f"[dry-run] {spec.name} done",
         "session_id": "dry-run", "total_cost_usd": 0.0,
         "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                   "cache_creation_input_tokens": 0},
         **({"structured_output": structured} if structured is not None else {})},
    ]
