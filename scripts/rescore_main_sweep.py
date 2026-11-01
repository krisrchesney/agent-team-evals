"""Rescore study 2 main-sweep runs with and without hidden tests whose rule the repo does not settle.

The primary score is what the harness recorded. The second score is a sensitivity check chosen after
seeing the results, so it is labelled that way wherever it is quoted. Tasks are never changed.
Usage: python scripts/rescore_main_sweep.py SWEEP_ROOT results/a.jsonl [results/b.jsonl ...]
"""
import collections
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ate import grade, tasks  # noqa: E402

# See docs/study2-main-sweep.md for why each of these is debatable.
DEBATABLE = {
    "t22-stock-holds": {"test_capture_event", "test_release", "test_create_event"},
    "t38-refund-policy": {"test_r1_refund_view", "test_r1_reason_has_a_default", "test_r2_ledger_ref_is_the_reason"},
    "t40-shift-swap": {"test_accept_event"},
}
CONFIGS = ["A", "AS", "D", "A2", "B"]


def failing_tests(root, r):
    """Every failing test in the run. Sweeps before the grade.py fix kept only the last 1,500 characters of
    output, so regrade the kept worktree once (no model call) and check it matches the recorded counts."""
    full = Path(root) / r["sweep_id"] / f'{r["task_id"]}__{r["config_id"]}__r{r["rep"]}' / "hidden_tests_full.txt"
    if not full.exists():
        t = grade.grade(tasks.load_task(r["task_id"]), r["worktree"])
        if (t["passed"], t["total"]) != (r["tests"]["passed"], r["tests"]["total"]):
            print("REGRADE DIFFERS", r["run_id"], t["passed"], t["total"], r["tests"], file=sys.stderr)
        full.write_text(t["output"], encoding="utf-8")
    return set(re.findall(r"^(?:FAIL|ERROR): (\w+)", full.read_text(encoding="utf-8", errors="replace"), re.M))


def sign_test(wins, losses):
    n = wins + losses
    if not n:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(wins, losses) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def main(root, paths):
    runs = {}
    for p in paths:
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            if r["status"] in ("passed", "failed"):  # limit-cut runs are void, not fails
                failed = failing_tests(root, r)
                strict = r["status"] == "passed"
                lenient = strict or not (failed - DEBATABLE.get(r["task_id"], set()))
                runs[(r["task_id"], r["config_id"], r["rep"])] = (strict, lenient, sum(r["tokens"].values()))
    tasks = sorted({k[0] for k in runs})
    for name, idx in (("recorded", 0), ("without debatable tests", 1)):
        print(f"\n{name}")
        for t in tasks:
            cells = []
            for c in CONFIGS:
                got = [v for k, v in runs.items() if k[0] == t and k[1] == c]
                cells.append(f"{c} {sum(v[idx] for v in got)}/{len(got)}")
            print(f"  {t:26s} " + "  ".join(cells))
        print(f"  {'all':26s} " + "  ".join(
            f"{c} {sum(v[idx] for k, v in runs.items() if k[1] == c)}/{sum(1 for k in runs if k[1] == c)}" for c in CONFIGS))
        for c in CONFIGS[1:]:
            w = l = 0
            for (t, cfg, rep), v in runs.items():
                if cfg == c and (t, "A", rep) in runs:
                    a = runs[(t, "A", rep)][idx]
                    w += v[idx] and not a
                    l += a and not v[idx]
            print(f"  {c} vs A, same task and rep: {c} only {w}, A only {l}, sign test p={sign_test(w, l):.2f}")
    print("\ntokens")
    for c in CONFIGS:
        vals = [v[2] for k, v in runs.items() if k[1] == c]
        strict = sum(v[0] for k, v in runs.items() if k[1] == c)
        lenient = sum(v[1] for k, v in runs.items() if k[1] == c)
        print(f"  {c}: {sum(vals) // len(vals):,} per run; per pass {sum(vals) // max(strict, 1):,} recorded, "
              f"{sum(vals) // max(lenient, 1):,} without debatable tests")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
