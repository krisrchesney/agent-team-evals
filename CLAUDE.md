# agent-team-evals: rules for every Claude session and agent

This repo is an eval harness. It measures whether multi-agent Claude Code setups (configs B, C)
beat a single agent (config A) on coding tasks, on pass rate, cost and wall-clock time.
Read DESIGN.md before your first ticket. It explains every choice below.

## Workflow
- Work comes from TASKS.md. Take one Ready ticket, set it to "In progress (<branch>)", and touch
  only the files it owns.
- Work in your own worktree and branch, `ticket/T-<n>-<slug>`, never on main.
- `python scripts/check.py` must pass before you say a ticket is done. A Stop hook runs it.
  It makes no API calls.
- When done: commit on your branch, set the ticket to "Review", and say so. Don't merge or push.
  The user merges after the `reviewer` agent (.claude/agents/reviewer.md) approves.
- Never delete, skip or loosen a test, weaken a task's hidden tests, or edit scripts/check.py or
  .claude/hooks/ to get a green check, unless the ticket says to.
- Commit identity: `git -c user.name="Kacey Chesney" -c user.email=k.c.chesney2016@gmail.com commit ...`
- This machine has git 2.16: no `git worktree add -q`, no `git worktree remove`.

## Money: the rule that matters most
- **Never start a real run** (`python -m ate run` without `--dry-run`) unless the user asked for that
  exact run in this session and saw its estimate. Every real run needs `--max-total-usd` and `--yes`.
  Dry runs and `validate` are free; use them freely.
- Runs use the user's Claude subscription through the clean profile (`auth: subscription`). Never
  switch to `auth: api_key`, set an API key, or weaken `child_env` / `check_subscription_auth`: the
  user does not want to spend any extra money.
- Never invent or "fill in" cost, token or pass-rate numbers. Only numbers from results/*.jsonl
  produced by a real sweep go into README or DESIGN, with the sweep id next to them.

## Models
- Default to Sonnet (`"model": "sonnet"` in configs/defaults.json) for sweeps, roles and dev agents.
- Agent files (configs/*/.claude/agents/, .claude/agents/) never set a pricier `model:`; omit it or
  use `inherit`/`sonnet`. A test and a runtime check enforce this for benchmark roles.
- An Opus comparison is a separate, opt-in sweep (`--model opus`) run only after asking the user.

## Fairness rules (the reviewer checks these)
- Configs differ only in team structure. Same model, budget, turn limit, tools and permission mode
  for all of them (configs/defaults.json). The builder and reviewer role files are identical in
  configs/B and configs/C (a test enforces this).
- Hidden tests and solutions must never be reachable from a worktree before grading. Worktrees
  live in work_root (default D:/ate-work), outside this repo.
- Read-only roles (planner, reviewer) never get Edit or Write.
- Don't change a task after real results exist for it. Add a new task id instead (t01 → t01b).

## Conventions
- Harness code (ate/) is Python stdlib only. A plotting script may use matplotlib as a dev-only
  dependency; nothing in ate/ may import it.
- Tasks: stdlib Python; prompt.md has numbered requirements; every hidden test traces to one;
  hidden tests are deterministic (inject clocks, seeds) and run in seconds; reference
  solution in solution/; `python -m ate validate --tasks <id>` must say OK.
- Write tasks from scratch. Don't copy public benchmarks (SWE-bench, HumanEval, LeetCode); their
  solutions are likely in training data.
- Results JSONL shape is docs/results.schema.json. Changing a field's meaning bumps SCHEMA_VERSION
  in ate/__init__.py.
- C: is nearly full. Large outputs (worktrees, transcripts) go under work_root on D:.

## Lessons
One line per finished ticket: what went wrong or what review caught. Added on main by the
session that merges.
