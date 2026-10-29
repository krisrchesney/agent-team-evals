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


def summarise(records):
    by_cfg = defaultdict(list)
    for r in records:
        by_cfg[r["config_id"]].append(r)
    rows = []
    for cid in sorted(by_cfg):
        rs = by_cfg[cid]
        n = len(rs)
        k = sum(r["passed"] for r in rs)
        lo, hi = wilson(k, n)
        cost = sum(r["cost_usd"] for r in rs)
        rows.append({
            "config": cid, "runs": n, "passed": k, "pass_rate": k / n if n else 0.0, "ci": (lo, hi),
            "partial": statistics.mean(r["tests"]["passed"] / r["tests"]["total"] if r["tests"]["total"] else 0 for r in rs),
            "mean_cost": cost / n if n else 0.0,
            "cost_per_pass": cost / k if k else float("inf"),
            "median_wall": statistics.median(r["agent_wall_s"] for r in rs),
            "mean_tokens": statistics.mean(r["tokens"]["input"] + r["tokens"]["output"]
                                           + r["tokens"]["cache_read"] + r["tokens"]["cache_creation"] for r in rs),
            "fix_rate": sum(r["fix_round"] for r in rs) / n if n else 0.0,
        })
    return rows


def per_task(records):
    grid = defaultdict(lambda: defaultdict(list))
    for r in records:
        grid[r["task_id"]][r["config_id"]].append(r["passed"])
    return grid


def render(records):
    if not records:
        return "no records"
    dry = any(r["dry_run"] for r in records)
    out = []
    if dry:
        out.append("> DRY RUN data: no API calls were made; pass rates reflect unmodified snapshots.\n")
    out.append("| config | runs | pass rate (95% CI) | hidden tests passed | mean $ / run | $ per pass | median wall s | mean tokens | fix round ran |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for s in summarise(records):
        cpp = "n/a" if s["cost_per_pass"] == float("inf") else f"{s['cost_per_pass']:.3f}"
        out.append(f"| {s['config']} | {s['runs']} | {s['pass_rate']:.0%} ({s['ci'][0]:.0%}-{s['ci'][1]:.0%}) | "
                   f"{s['partial']:.0%} | {s['mean_cost']:.3f} | {cpp} | {s['median_wall']:.1f} | "
                   f"{s['mean_tokens']:,.0f} | {s['fix_rate']:.0%} |")
    grid = per_task(records)
    cfgs = sorted({r["config_id"] for r in records})
    out.append("\nPer task (passes / runs):\n")
    out.append("| task | " + " | ".join(cfgs) + " |")
    out.append("|---|" + "---|" * len(cfgs))
    for tid in sorted(grid):
        cells = [f"{sum(grid[tid][c])}/{len(grid[tid][c])}" if grid[tid][c] else "-" for c in cfgs]
        out.append(f"| {tid} | " + " | ".join(cells) + " |")
    problems = [r for r in records if r["status"] in ("harness_error",) or r["leak_suspected"] or r["read_only_violations"]]
    if problems:
        out.append("\nFlags:")
        for r in problems:
            out.append(f"- {r['run_id']}: status={r['status']} leak={r['leak_suspected']} "
                       f"read_only_violations={r['read_only_violations']} error={r['error']}")
    return "\n".join(out)
