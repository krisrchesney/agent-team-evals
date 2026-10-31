"""CLI.

  python -m ate list                         tasks and configs
  python -m ate validate [--tasks t01]       each task: snapshot fails hidden tests, solution passes
  python -m ate run --dry-run                whole pipeline, no API calls, no plan usage
  python -m ate auth                         is the clean subscription profile signed in?
  python -m ate run --tasks t01 --configs A --reps 1 --max-total-api-equiv 0.5 --yes   real run (uses plan usage)
  python -m ate run --resume <sweep_id> ...  continue after a usage-limit stop (same flags)
  python -m ate report results/<sweep>.jsonl
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import REPO_ROOT, claude, config, grade, pipeline, report, results, tasks


def _harness_sha():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, capture_output=True,
                              text=True).stdout.strip() or None
    except OSError:
        return None


def cmd_list(_args):
    print("tasks:  ", ", ".join(tasks.list_tasks()))
    for cid in config.list_configs():
        cfg = config.load_config(cid)
        print(f"config {cid}: {cfg['name']}  stages={[s['name'] for s in cfg['stages']]}")
    print("claude: ", claude.find_claude() or "NOT FOUND (set CLAUDE_BIN)")


def cmd_validate(args):
    """A task is valid only if its hidden tests fail on the snapshot and pass on the reference solution."""
    bad = 0
    for tid in tasks.resolve(args.tasks):
        task = tasks.load_task(tid)
        with tempfile.TemporaryDirectory() as tmp:
            snap = Path(tmp) / "snap"
            shutil.copytree(task.repo, snap)
            before = grade.grade(task, snap)
            shutil.copytree(task.solution, snap, dirs_exist_ok=True)
            visible = grade.run_unittest(snap, "tests", task.test_timeout_s)
            after = grade.grade(task, snap)
        ok = (not before["ok"]) and after["ok"] and visible["ok"]
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {tid}: snapshot {before['passed']}/{before['total']} hidden "
              f"(must fail), solution {after['passed']}/{after['total']} hidden + "
              f"{visible['passed']}/{visible['total']} visible (must pass)")
        if not ok and args.verbose:
            print(after["output_tail"])
    return 1 if bad else 0


def _estimate(task_ids, config_ids, reps, defaults):
    """Rough pre-run estimate: stage count x a per-stage guess from configs/defaults.json."""
    per_stage = float(defaults["estimate_api_equiv_usd_per_stage"])
    total = 0.0
    for cid in config_ids:
        cfg = config.load_config(cid)
        stages = 0
        for st in cfg["stages"]:
            if "run" in st:
                continue  # harness-run stage: no model call
            stages += cfg.get("max_subtasks", 3) if "foreach" in st else 1
        total += stages * cfg.get("best_of", 1) * per_stage * len(task_ids) * reps  # worst case: every try runs
    cap = float(defaults["run_cap_api_equiv_usd"]) * len(task_ids) * len(config_ids) * reps
    return round(total, 2), round(cap, 2)


def cmd_run(args):
    defaults = config.load_defaults()
    if args.model:
        defaults["model"] = args.model
    if args.run_cap is not None:
        defaults["run_cap_api_equiv_usd"] = args.run_cap
    work_root = Path(args.work_root or defaults["work_root"])
    task_ids = tasks.resolve(args.tasks)
    config_ids = args.configs.split(",") if args.configs != "all" else config.list_configs()
    n_runs = len(task_ids) * len(config_ids) * args.reps
    est, cap = _estimate(task_ids, config_ids, args.reps, defaults)
    binary = claude.find_claude()

    subscription = defaults.get("auth", "subscription") == "subscription"
    print(f"plan: {len(task_ids)} tasks x {len(config_ids)} configs x {args.reps} reps = {n_runs} runs, "
          f"model={defaults['model']}, auth={defaults.get('auth', 'subscription')}")
    if args.dry_run:
        print("mode: DRY RUN (fake CLI, no plan usage)" + (" + oracle solutions" if args.oracle else ""))
    else:
        if subscription:
            print(f"usage estimate: {n_runs} runs, roughly ${est:.2f} API-equivalent "
                  f"(a yardstick, not a charge; nothing is billed). Runaway-loop cap: "
                  f"${defaults['run_cap_api_equiv_usd']:.2f} API-equivalent per run, ${cap:.2f} if every run hit it.")
            print("note your claude.ai usage bar before and after, and keep 'extra usage' off.")
        else:
            print(f"estimate: ~${est:.2f}, billed to the API key (cap ${defaults['run_cap_api_equiv_usd']:.2f}/run)")
        if not binary:
            print("claude CLI not found; set CLAUDE_BIN")
            return 2
        ok, msg = claude.check_subscription_auth(binary, defaults)
        print(f"auth: {msg}")
        if not ok:
            print("refusing to start. Sign the clean profile in once, in PowerShell:\n  "
                  + claude.login_command(binary, defaults))
            return 2
        if args.max_total_api_equiv is None:
            print("refusing to start: pass --max-total-api-equiv, a sweep-wide runaway-loop cap in API-equivalent units")
            return 2
        if not args.yes:
            print("refusing to start: re-run with --yes after reading the estimate above")
            return 2

    results_dir = Path(args.results_dir) if args.results_dir else REPO_ROOT / "results"
    previous = []
    if args.resume:
        sweep_id = args.resume
        results_path = results_dir / f"{sweep_id}.jsonl"
        if not results_path.exists():
            print(f"no results file for sweep {sweep_id} in {results_dir}")
            return 2
        previous = results.read([results_path])
    else:
        sweep_id = (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    + ("-dry" if args.dry_run else "") + ("-oracle" if args.oracle else ""))
        results_path = results_dir / f"{sweep_id}.jsonl"
    plan = _plan_keys(task_ids, config_ids, args.reps)
    done = {(r["task_id"], r["config_id"], r["rep"]) for r in previous
            if r["status"] not in pipeline.RETRYABLE}
    attempts = {}
    for r in previous:
        key = (r["task_id"], r["config_id"], r["rep"])
        attempts[key] = max(attempts.get(key, 0), r.get("attempt", 1))
    if previous:
        print(f"resume: {len(done & plan)} of {n_runs} runs already done")

    version = "dry-run" if args.dry_run else claude.claude_version(binary)
    sha = _harness_sha()
    spent = sum(r["api_equiv_usd"] for r in previous)  # the cap covers the whole sweep, resumed or not
    halt = None
    # Interleave configs within each task+rep so time-of-day effects hit every config equally.
    for rep in range(1, args.reps + 1):
        for tid in task_ids:
            task = tasks.load_task(tid)
            for cid in config_ids:
                key = (tid, cid, rep)
                if halt or key in done:
                    continue
                if args.max_total_api_equiv is not None and spent >= args.max_total_api_equiv:
                    halt = f"sweep reached its cap of {args.max_total_api_equiv} API-equivalent (used {spent:.2f})"
                    continue
                cfg = config.load_config(cid)
                rec = pipeline.run_one(task, cfg, rep, defaults=defaults, sweep_id=sweep_id,
                                       work_root=work_root, results_path=results_path, binary=binary,
                                       claude_version=version, harness_sha=sha,
                                       fake=(pipeline.make_fake(task if args.oracle else None)
                                             if args.dry_run else None),
                                       keep_worktree=not args.cleanup, attempt=attempts.get(key, 0) + 1)
                spent += rec["api_equiv_usd"]
                stages = "+".join(s["name"] for s in rec["stages"])
                print(f"  {tid} {cid} r{rep}: {rec['status']:<15} tests {rec['tests']['passed']}/"
                      f"{rec['tests']['total']}  {sum(rec['tokens'].values()):,} tok  {rec['num_turns']} turns  "
                      f"{rec['agent_wall_s']:.1f}s  (~${rec['api_equiv_usd']:.2f} API-equiv)  [{stages}]"
                      + (f"  ERROR {rec['error']}" if rec["error"] else "")
                      + (f"  ISOLATION {rec['isolation_flags']}" if rec.get("isolation_flags") else ""))
                if rec["status"] == "rate_limited":
                    halt = "usage limit reached"
                elif rec["status"] == "auth_error":
                    halt = "a stage did not use the subscription login"
                elif rec.get("isolation_flags") and not args.dry_run:
                    halt = "personal Claude setup leaked into a run"
    if halt:
        print(f"stopped: {halt}. Continue later with the same flags plus: --resume {sweep_id}")
    print(f"results: {results_path}")
    total_tok = sum(sum(r["tokens"].values()) for r in results.read([results_path])) if results_path.exists() else 0
    print(f"sweep usage: {total_tok:,} tokens, ~${spent:.2f} API-equivalent"
          + (" (not a charge)" if subscription else " (billed)"))
    return 3 if halt else 0


def _plan_keys(task_ids, config_ids, reps):
    return {(t, c, r) for r in range(1, reps + 1) for t in task_ids for c in config_ids}


def cmd_auth(_args):
    defaults = config.load_defaults()
    binary = claude.find_claude()
    if not binary:
        print("claude CLI not found; set CLAUDE_BIN")
        return 2
    print(f"claude CLI: {binary} (version {claude.claude_version(binary)})")
    print(f"auth mode: {defaults.get('auth', 'subscription')}")
    print(f"clean profile: {defaults.get('claude_config_dir')}")
    status, err = claude.auth_status(binary, defaults)
    print(f"claude auth status: {status if status is not None else err}")
    ok, msg = claude.check_subscription_auth(binary, defaults)
    print(("OK: " if ok else "NOT READY: ") + msg)
    if not ok:
        print("Sign in once, in PowerShell (opens your browser):\n  " + claude.login_command(binary, defaults))
    return 0 if ok else 1


def cmd_report(args):
    print(report.render(report.load(args.files)))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m ate", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    v = sub.add_parser("validate")
    v.add_argument("--tasks", default="all")
    v.add_argument("-v", "--verbose", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--tasks", default="all", help="'all' or comma list of ids/prefixes")
    r.add_argument("--configs", default="all", help="'all' or e.g. A,B")
    r.add_argument("--reps", type=int, default=3)
    r.add_argument("--dry-run", action="store_true", help="fake CLI: no API calls, no plan usage")
    r.add_argument("--oracle", action="store_true",
                   help="with --dry-run: fake builders copy in the reference solution (tests the pass path)")
    r.add_argument("--max-total-api-equiv", type=float, help="runaway-loop cap for the whole sweep, in API-equivalent dollars (required for real runs)")
    r.add_argument("--run-cap", type=float, help="override the per-run runaway-loop cap (API-equivalent dollars)")
    r.add_argument("--model", help="override configs/defaults.json model")
    r.add_argument("--work-root", help="where seeds/worktrees/logs go (default from defaults.json)")
    r.add_argument("--results-dir", help="default: results/")
    r.add_argument("--cleanup", action="store_true", help="delete worktrees after grading")
    r.add_argument("--yes", action="store_true", help="confirm a real (non-dry) run")
    r.add_argument("--resume", metavar="SWEEP_ID",
                   help="continue a sweep: skip finished runs, re-run rate_limited/auth_error/harness_error ones")
    sub.add_parser("auth", help="is the clean subscription profile signed in?")
    rp = sub.add_parser("report")
    rp.add_argument("files", nargs="+")
    args = p.parse_args(argv)
    return {"list": cmd_list, "validate": cmd_validate, "run": cmd_run, "report": cmd_report,
            "auth": cmd_auth}[args.cmd](args) or 0


if __name__ == "__main__":
    sys.exit(main())
