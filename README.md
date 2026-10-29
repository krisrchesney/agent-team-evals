# agent-team-evals

Does a team of Claude agents (planner, builder, reviewer) write better code than one agent, and
what does it use? This harness runs the same coding tasks through three setups and measures
pass rate on hidden tests, usage (tokens and turns), and wall-clock time.

| Config | Setup |
|---|---|
| A | one headless Claude Code agent (`claude -p`) |
| B | builder + read-only reviewer, one round of fixes |
| C | planner → builder(s) → reviewer → one fix round |

**Status:** scaffolded and running end to end in dry-run mode. No real benchmark has run yet, so
there are no results. See [DESIGN.md](DESIGN.md) for how and why, and [TASKS.md](TASKS.md) for what's next.

## Try it (no API calls, no plan usage)

```bash
python -m ate list                       # tasks, configs, where the claude CLI is
python -m ate validate                   # each task: hidden tests fail on the start code, pass on the reference
python -m ate run --dry-run --reps 1     # whole pipeline with a fake CLI (no plan usage)
python -m ate run --dry-run --oracle --reps 1   # same, fake builders apply the reference solution
python -m ate report results/<sweep>.jsonl
python scripts/check.py                  # everything above as one health check
```

Real runs use your Claude Pro/Max subscription (plan usage, no per-token billing) through a clean
profile that holds only a login. Turn off "extra usage" in claude.ai settings first, then:

```bash
python -m ate auth                       # signed in? if not, prints the one-time login command
python -m ate run --tasks t01 --configs A --reps 1 --run-cap 0.5 --max-total-api-equiv 0.5 --yes
```

A run that hits your usage limit stops the sweep; continue it later with `--resume <sweep_id>`.

Python 3.12, standard library only. Worktrees and transcripts go to `D:/ate-work`
(`work_root` in configs/defaults.json).
