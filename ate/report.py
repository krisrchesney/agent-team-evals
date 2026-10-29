"""Summarise results JSONL into a markdown table (stdlib only; charts are a separate ticket)."""
import math
import statistics
from collections import defaultdict

from . import results


def load(paths):
    return results.read(paths)


def wilson(k, n, z=1.96):
    """95% Wilson interval for a pass rate. Honest for small n, unlike +/- 1.96*sqrt(p(1-p)/n)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


RETRYABLE = ("rate_limited", "auth_error", "harness_error")


def counted(records):
    """Runs that say something about the config. Retryable failures are left out."""
    return [r for r in records if r["status"] not in RETRYABLE]


def total_tokens(r):
    t = r["tokens"]
    return t["input"] + t["output"] + t["cache_read"] + t["cache_creation"]


def summarise(records):
    """Usage first: tokens, turns and wall time. API-equivalent dollars are a yardstick, not a charge."""
    by_cfg = defaultdict(list)
    for r in counted(records):
        by_cfg[r["config_id"]].append(r)
    rows = []
    for cid in sorted(by_cfg):
        rs = by_cfg[cid]
        n = len(rs)
        k = sum(r["passed"] for r in rs)
        lo, hi = wilson(k, n)
        tokens = sum(total_tokens(r) for r in rs)
        rows.append({
            "config": cid, "runs": n, "passed": k, "pass_rate": k / n if n else 0.0, "ci": (lo, hi),
            "partial": statistics.mean(r["tests"]["passed"] / r["tests"]["total"] if r["tests"]["total"] else 0 for r in rs),
            "mean_tokens": tokens / n if n else 0.0,
            "mean_output": statistics.mean(r["tokens"]["output"] for r in rs),
            "tokens_per_pass": tokens / k if k else float("inf"),
            "mean_turns": statistics.mean(r["num_turns"] for r in rs),
            "median_wall": statistics.median(r["agent_wall_s"] for r in rs),
            "mean_api_equiv": statistics.mean(r["api_equiv_usd"] for r in rs),
            "fix_rate": sum(r["fix_round"] for r in rs) / n if n else 0.0,
        })
    return rows


def per_task(records):
    grid = defaultdict(lambda: defaultdict(list))
    for r in counted(records):
        grid[r["task_id"]][r["config_id"]].append(r["passed"])
    return grid


def render(records):
    if not records:
        return "no records"
    if not counted(records):
        return f"no countable records ({len(records)} retryable); re-run with --resume"
    dry = any(r["dry_run"] for r in records)
    out = []
    if dry:
        out.append("> DRY RUN data: fake agents, no API calls, no plan usage. These numbers say nothing about the configs.\n")
    out.append("| config | runs | pass rate (95% CI) | hidden tests passed | tokens / run | output tokens / run "
               "| tokens / pass | turns / run | median wall s | fix round ran | API-equiv $ / run (not a charge) |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for s in summarise(records):
        tpp = "n/a" if s["tokens_per_pass"] == float("inf") else f"{s['tokens_per_pass']:,.0f}"
        out.append(f"| {s['config']} | {s['runs']} | {s['pass_rate']:.0%} ({s['ci'][0]:.0%}-{s['ci'][1]:.0%}) | "
                   f"{s['partial']:.0%} | {s['mean_tokens']:,.0f} | {s['mean_output']:,.0f} | {tpp} | "
                   f"{s['mean_turns']:.1f} | {s['median_wall']:.1f} | {s['fix_rate']:.0%} | "
                   f"{s['mean_api_equiv']:.3f} |")
    grid = per_task(records)
    cfgs = sorted({r["config_id"] for r in records})
    out.append("\nPer task (passes / runs):\n")
    out.append("| task | " + " | ".join(cfgs) + " |")
    out.append("|---|" + "---|" * len(cfgs))
    for tid in sorted(grid):
        cells = [f"{sum(grid[tid][c])}/{len(grid[tid][c])}" if grid[tid][c] else "-" for c in cfgs]
        out.append(f"| {tid} | " + " | ".join(cells) + " |")
    skipped = len(records) - len(counted(records))
    if skipped:
        out.append(f"\n{skipped} run(s) left out (rate_limited / auth_error / harness_error); re-run with --resume.")
    if any(r.get("auth") == "subscription" for r in records):
        out.append("\nRuns use the plan's usage. Tokens, turns and time are the usage metrics; the dollar column is Claude Code's API-equivalent estimate, for comparing configs, not a charge.")
    problems = [r for r in records if r["status"] in RETRYABLE or r["leak_suspected"]
                or r["read_only_violations"] or r.get("isolation_flags")]
    if problems:
        out.append("\nFlags:")
        for r in problems:
            out.append(f"- {r['run_id']}: status={r['status']} leak={r['leak_suspected']} "
                       f"read_only_violations={r['read_only_violations']} "
                       f"isolation={r.get('isolation_flags')} error={r['error']}")
    return "\n".join(out)
