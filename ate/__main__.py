"""CLI.

  python -m ate list                         tasks and configs
  python -m ate validate [--tasks t01]       each task: snapshot fails hidden tests, solution passes
  python -m ate run --dry-run                whole pipeline, no API calls, zero cost
  python -m ate run --tasks t01 --configs A --reps 1 --max-total-usd 1 --yes    real (paid) run
  python -m ate report results/<sweep>.jsonl
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import REPO_ROOT, claude, config, grade, pipeline, report, tasks


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
    per_stage = float(defaults["estimate_usd_per_stage"])
    total = 0.0
    for cid in config_ids:
        cfg = config.load_config(cid)
        stages = 0
        for st in cfg["stages"]:
            stages += cfg.get("max_subtasks", 3) if "foreach" in st else 1
        total += stages * per_stage * len(task_ids) * reps
    cap = float(defaults["run_budget_usd"]) * len(task_ids) * len(config_ids) * reps
    return round(total, 2), round(cap, 2)


def cmd_run(args):
    defaults = config.load_defaults()
    if args.model:
        defaults["model"] = args.model
    if args.run_budget is not None:
        defaults["run_budget_usd"] = args.run_budget
    work_root = Path(args.work_root or defaults["work_root"])
    task_ids = tasks.resolve(args.tasks)
    config_ids = args.configs.split(",") if args.configs != "all" else config.list_configs()
    n_runs = len(task_ids) * len(config_ids) * args.reps
    est, cap = _estimate(task_ids, config_ids, args.reps, defaults)
    binary = claude.find_claude()

    print(f"plan: {len(task_ids)} tasks x {len(config_ids)} configs x {args.reps} reps = {n_runs} runs, "
          f"model={defaults['model']}")
    if args.dry_run:
        print("mode: DRY RUN (fake CLI, no API calls, $0.00)" + (" + oracle solutions" if args.oracle else ""))
    else:
        print(f"estimate: ~${est:.2f} (worst case if every run hits its ${defaults['run_budget_usd']:.2f} cap: ${cap:.2f})")
        if not binary:
            print("claude CLI not found; set CLAUDE_BIN")
            return 2
        if args.max_total_usd is None:
            print("refusing to start: pass --max-total-usd for any paid run")
            return 2
        if not args.yes:
            print("refusing to start: re-run with --yes after reading the estimate above")
            return 2

    sweep_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ("-dry" if args.dry_run else "") + ("-oracle" if args.oracle else "")
    results_dir = Path(args.results_dir) if args.results_dir else REPO_ROOT / "results"
    results_path = results_dir / f"{sweep_id}.jsonl"
    version = "dry-run" if args.dry_run else claude.claude_version(binary)
    sha = _harness_sha()
    spent = 0.0
    # Interleave configs within each task+rep so time-of-day effects hit every config equally.
    for rep in range(1, args.reps + 1):
        for tid in task_ids:
            task = tasks.load_task(tid)
            for cid in config_ids:
                if args.max_total_usd is not None and spent >= args.max_total_usd:
                    print(f"stopping: spent ${spent:.2f} >= --max-total-usd {args.max_total_usd}")
                    break
                cfg = config.load_config(cid)
                rec = pipeline.run_one(task, cfg, rep, defaults=defaults, sweep_id=sweep_id,
                                       work_root=work_root, results_path=results_path, binary=binary,
                                       claude_version=version, harness_sha=sha,
                                       fake=(pipeline.make_fake(task if args.oracle else None)
                                             if args.dry_run else None),
                                       keep_worktree=not args.cleanup)
                spent += rec["cost_usd"]
                stages = "+".join(s["name"] for s in rec["stages"])
                print(f"  {tid} {cid} r{rep}: {rec['status']:<15} tests {rec['tests']['passed']}/"
                      f"{rec['tests']['total']}  ${rec['cost_usd']:.3f}  {rec['agent_wall_s']:.1f}s  [{stages}]"
                      + (f"  ERROR {rec['error']}" if rec["error"] else ""))
    print(f"results: {results_path}")
    print(f"total spend: ${spent:.3f}")
    return 0


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
    r.add_argument("--dry-run", action="store_true", help="fake CLI: no API calls, $0")
    r.add_argument("--oracle", action="store_true",
                   help="with --dry-run: fake builders copy in the reference solution (tests the pass path)")
    r.add_argument("--max-total-usd", type=float, help="stop launching runs once spend reaches this (required for paid runs)")
    r.add_argument("--run-budget", type=float, help="override per-run cap (USD)")
    r.add_argument("--model", help="override configs/defaults.json model")
    r.add_argument("--work-root", help="where seeds/worktrees/logs go (default from defaults.json)")
    r.add_argument("--results-dir", help="default: results/")
    r.add_argument("--cleanup", action="store_true", help="delete worktrees after grading")
    r.add_argument("--yes", action="store_true", help="confirm a paid run")
    rp = sub.add_parser("report")
    rp.add_argument("files", nargs="+")
    args = p.parse_args(argv)
    return {"list": cmd_list, "validate": cmd_validate, "run": cmd_run, "report": cmd_report}[args.cmd](args) or 0


if __name__ == "__main__":
    sys.exit(main())
