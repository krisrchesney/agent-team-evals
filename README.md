# agent-team-evals

Does a team of Claude agents (planner, builder, reviewer) write better code than one agent, and
what does it cost? This harness runs the same coding tasks through three setups and measures
pass rate on hidden tests, dollars and tokens, and wall-clock time.

| Config | Setup |
|---|---|
| A | one headless Claude Code agent (`claude -p`) |
| B | builder + read-only reviewer, one round of fixes |
| C | planner → builder(s) → reviewer → one fix round |

**Status:** scaffolded and running end to end in dry-run mode. No paid benchmark has run yet, so
there are no results. See [DESIGN.md](DESIGN.md) for how and why, and [TASKS.md](TASKS.md) for what's next.

## Try it (free, no API calls)

```bash
python -m ate list                       # tasks, configs, where the claude CLI is
python -m ate validate                   # each task: hidden tests fail on the start code, pass on the reference
python -m ate run --dry-run --reps 1     # whole pipeline with a fake CLI ($0)
python -m ate run --dry-run --oracle --reps 1   # same, fake builders apply the reference solution
python -m ate report results/<sweep>.jsonl
python scripts/check.py                  # everything above as one health check
```

A paid run needs an `ANTHROPIC_API_KEY`, a spend cap and explicit confirmation:

```bash
python -m ate run --tasks t01 --configs A --reps 1 --run-budget 0.5 --max-total-usd 0.5 --yes
```

Python 3.12, standard library only. Worktrees and transcripts go to `D:/ate-work`
(`work_root` in configs/defaults.json).
