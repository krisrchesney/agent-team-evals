"""How many tasks and runs does a sweep need to detect a pass-rate gap? Simulation, no API calls.

  python scripts/power.py
  python scripts/power.py --tasks 10,15,20 --reps 3,5 --gaps 0.15,0.25 --base 0.3,0.8

Model: each task has a single-agent pass chance drawn uniformly from --base; the other config
passes that task with the chance plus the gap (capped at 1). Each sweep is analysed the way
`python -m ate report` does it: per-task pass-rate differences, a bootstrap over tasks, and a
95% interval. Power = the share of simulated sweeps whose interval is entirely above zero.
"""
import argparse
import random


def interval(diffs, rng, n_boot):
    means = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(n_boot))
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]


def power(n_tasks, reps, gap, base, sims, n_boot, rng):
    hits = 0
    for _ in range(sims):
        diffs = []
        for _ in range(n_tasks):
            p = rng.uniform(*base)
            q = min(1.0, p + gap)
            a = sum(rng.random() < p for _ in range(reps)) / reps
            b = sum(rng.random() < q for _ in range(reps)) / reps
            diffs.append(b - a)
        lo, _ = interval(diffs, rng, n_boot)
        hits += lo > 0
    return hits / sims


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tasks", default="5,10,15,20,30")
    p.add_argument("--reps", default="3,5")
    p.add_argument("--gaps", default="0.10,0.15,0.20,0.30")
    p.add_argument("--base", default="0.3,0.8", help="range of single-agent pass chances per task")
    p.add_argument("--sims", type=int, default=400)
    p.add_argument("--boot", type=int, default=400)
    p.add_argument("--seed", type=int, default=1)
    a = p.parse_args(argv)
    rng = random.Random(a.seed)
    base = tuple(float(x) for x in a.base.split(","))
    gaps = [float(g) for g in a.gaps.split(",")]
    print(f"power to detect a pass-rate gap (single-agent pass chance per task {base[0]:.0%}-{base[1]:.0%}, "
          f"{a.sims} simulated sweeps each)")
    print(f"{'tasks':>5} {'reps':>4} {'runs/config':>11}  " + "  ".join(f"gap {g:>4.0%}" for g in gaps))
    for n in (int(x) for x in a.tasks.split(",")):
        for r in (int(x) for x in a.reps.split(",")):
            row = [power(n, r, g, base, a.sims, a.boot, rng) for g in gaps]
            print(f"{n:>5} {r:>4} {n * r:>11}  " + "  ".join(f"{x:>8.0%}" for x in row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
