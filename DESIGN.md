# agent-team-evals: design

**Question.** On the same set of coding tasks, does a team of Claude agents beat a single agent?
"Beat" here covers three things: **pass rate** on tests the agents never saw, **cost** (tokens and
dollars), and **wall-clock time**.

| Config | What runs | Why it's in the study |
|---|---|---|
| **A** single agent | one `claude -p` run gets the task and works until it stops | The baseline. Most people use Claude Code this way. |
| **B** builder + reviewer | builder run → read-only reviewer run → at most **one** builder fix run if the reviewer says CHANGES_NEEDED | The cheapest "team": a second opinion from a fresh context. |
| **C** full team | read-only planner → 1–3 builder runs, one per subtask → reviewer → one fix run | The Boxwatch pattern (planner, builders, reviewer) in small form. |

Everything below is about keeping that comparison fair, measurable and cheap to repeat.

---

## 1. Tasks

### Format

```
tasks/<id>/
  task.json        id, title, category, difficulty, test_timeout_s
  prompt.md        what the agents are told (numbered requirements)
  repo/            the starting code: a tiny Python project with a few visible tests in tests/
  hidden_tests/    the grader. Agents never see these files.
  solution/        a reference fix, as files copied over repo/. Used only to validate the task.
```

**Why hidden tests?** If the grader is visible, agents can fit to it (or, in the worst case,
edit it). Hidden tests measure whether the code meets the *prompt*, the way a user would judge it.
The visible tests in `repo/tests/` are deliberately thin, like a real repo's, so "make the
visible tests pass" isn't enough.

**Why a reference solution?** `python -m ate validate` checks every task both ways: the hidden tests
must **fail** on the starting code (otherwise the task measures nothing) and **pass** on the
reference solution (otherwise the task is impossible or the tests are wrong). A broken task would
quietly drag every config's score down by the same amount and hide real differences.

**Why numbered requirements in the prompt?** Every hidden test traces back to a sentence in the
prompt. If an agent "fails" a test for behaviour the prompt never asked for, that's a task bug, not
an agent failure. Numbering also gives the planner and reviewer something concrete to check.

### Task set

Start with 5 hand-written tasks (2 are done, 3 are tickets), then grow to 20–30. Spread them across:

| Category | Example | Why it matters for the question |
|---|---|---|
| Bug fix + small feature | t01 slugify (done) | Single file. Teams should add cost and little value; a good control. |
| Feature with edge cases | t02 TTL cache (done) | Spec has interacting rules. A reviewer might catch the missed one. |
| Multi-file change | t03 CSV report CLI (ticket) | Where a planner should help, if it ever does. |
| Subtle bug hunt | t04 interval merge (ticket) | Tests whether a second reader finds what the first missed. |
| Spec with an ambiguity | t05 config + env overrides (ticket) | Do teams resolve ambiguity better or just argue? |

Rules for new tasks (also in CLAUDE.md): stdlib-only Python, solvable by the reference in under ~150
lines, hidden tests are deterministic (inject clocks and randomness), each runs in seconds, and the task
passes `validate`. Write tasks yourself or adapt them from your own code. Don't copy public
benchmarks such as SWE-bench or HumanEval. Their solutions are probably in the model's training data,
and that would inflate every config equally.

---

## 2. How each config runs headless

### One stage = one `claude -p` call

Each stage is a separate headless Claude Code process. The command, as checked against
`claude --help` on CLI 2.1.299 and the CLI reference docs:

```
claude -p                                   # print mode: run the prompt, exit (prompt goes on stdin)
  --output-format stream-json --verbose     # every event to a log; the last event is the result object
  --model sonnet                            # identical for every config and stage
  --max-turns 40                            # stop a stuck loop
  --max-budget-usd <remaining run budget>   # hard dollar cap for this stage
  --permission-mode acceptEdits             # can edit files without asking
  --permission-prompts none                 # nobody is there to approve, so deny (don't hang)
  --tools Bash,Read,Edit,Write,Glob,Grep    # which tools exist (read-only stages drop Edit/Write)
  --allowedTools "Read,Edit,...,Bash(python -m unittest *),Bash(git diff *)"   # which run without asking
  --no-session-persistence                  # don't write transcripts into ~/.claude (C: is nearly full)
  --bare                                    # ignore ~/.claude hooks, plugins, memory and CLAUDE.md
  --agents <run>/agents.json --agent reviewer   # B and C: which role this stage plays
  --json-schema '<schema>'                  # reviewer and planner: structured output
```

**Why stream-json and not plain json?** `--output-format json` prints only the final result object
(`total_cost_usd`, `usage`, `modelUsage`, `num_turns`, `duration_ms`, `subtype`, `result`,
`structured_output`). `stream-json` ends with **that same object**, and before it we also get the
whole transcript. We save it per stage, so when C loses to A on a task you can read why. The
harness reads only the last `type: "result"` line for the numbers.

**Why `--bare`?** Without it, `claude -p` loads your personal `~/.claude` setup: your CLAUDE.md
(which tells Claude to print the CST time first), your plugins, hooks and memory. That would
contaminate the benchmark and make it unreproducible on another machine. Bare mode loads none of it.
Roles are passed explicitly with `--agents`. The catch is that **bare mode only accepts
`ANTHROPIC_API_KEY`**, not a subscription login. That suits a benchmark anyway: costs are real API
dollars, not estimates hidden inside a plan's rate limits. A `"bare": false` switch exists in
`configs/defaults.json` for subscription use, but it is untested (ticket T-11).

**Why the prompt goes on stdin.** `--allowedTools` and `--tools` take a variable number of values
and can swallow a positional prompt placed after them. Stdin avoids that.

### Roles: `.claude/agents/*.md`

Role files live where a real project keeps them: `configs/B/.claude/agents/` and
`configs/C/.claude/agents/`. They are ordinary subagent files (frontmatter: `name`,
`description`, `tools`, then the system prompt). The harness turns them into the JSON that
`--agents` takes, and `--agent <name>` makes that role the main agent for the stage.

- **builder** (B, C): implements, adds tests, must run the tests before stopping.
- **reviewer** (B, C): read-only. Checks each numbered requirement and returns
  `{verdict: APPROVE|CHANGES_NEEDED, findings: [...]}` through `--json-schema`.
- **planner** (C): read-only. Returns `{subtasks: [1–3 items], risks: [...]}`.

The builder and reviewer files are **byte-identical in B and C**, and a test enforces this. The only
difference between B and C is the planner and the split into subtasks. Otherwise a C-vs-B gap could
just come from better wording.

**Read-only is enforced, not just requested.** Read-only stages get no Edit/Write tools, and Bash is
limited to `python -m unittest`, `git diff` and `git status`. The harness also snapshots the working
tree before a read-only stage. If anything changed afterwards, it records a
`read_only_violations` entry and reverts the change.

### Who orchestrates: the harness, not the model

B and C could also be run as a single `claude -p` whose main agent calls subagents itself. We
don't do that (yet), because then the model decides whether review happens, how many fix rounds
there are, and whether the planner is used at all. The study would measure the model's
self-management instead of the team structure. Here the harness runs stages in a fixed order:

```
A:  solve
B:  build → review → fix (only if CHANGES_NEEDED)
C:  plan → build_1 … build_n (n = planner's subtasks, max 3) → review → fix (only if CHANGES_NEEDED)
```

That gives exactly "one round of fixes", and every token is billed to a named stage, so you can
say, for example, "the reviewer cost 18% of C's spend". An in-session variant (C-auto) is ticket
T-10, as a separate config, because how well Claude orchestrates subagents is its own question.

The fix round is a **fresh** builder process. It receives the task, the reviewer's findings and the
working tree as the reviewer saw it. It does not `--resume` the build session, because resuming
reports the conversation's cumulative cost and would blur the per-stage accounting. C's builders run
**sequentially in one worktree**: parallel builders would need merging, which is a different
experiment (ticket T-12).

### Isolation: git worktrees

For each task the harness makes a throwaway **seed repo** (`<work_root>/seeds/<task>`), which holds
`repo/` as a single commit. Every run gets `git worktree add` on its own branch from that commit:

- every run of a task starts from byte-identical files
- `git diff <seed>` is exactly what the agents changed (the `diff` field)
- runs can't see each other's edits, and you can open any worktree afterwards to inspect it
- it's cheap: these are tiny repos, and worktrees share one object store

`work_root` defaults to `D:/ate-work`, **outside this repo**, so an agent in a worktree can't walk up
into `tasks/*/hidden_tests`. Hidden tests are copied into the worktree (`_ate_hidden/`) only after
the last agent stage, and deleted after grading. The harness also scans every transcript for
`hidden_tests`, `_ate_hidden` and `agent-team-evals` and records any hit in `leak_suspected`.
This is not a sandbox: an agent with Bash could still search the disk. Real isolation (a container
with no route to this repo) is ticket T-9. Until then, check `leak_suspected` before trusting a sweep.

Known git 2.16 constraints on this machine: no `git worktree add -q` and no `git worktree remove`.
The harness deletes the folder, then runs `git worktree prune`.

---

## 3. Metrics

One JSONL record per (task, config, repetition). The schema is `docs/results.schema.json`, and
`ate/results.py` validates every record before writing it.

| Metric | Field | How it's measured |
|---|---|---|
| **Pass** (headline) | `passed` | every hidden test passes |
| Partial credit | `tests.passed / tests.total` | shows "almost" vs "nowhere", which pass/fail hides |
| **Cost, $** | `cost_usd` | sum of each stage's `total_cost_usd` (Claude Code's client-side estimate, subagents included) |
| **Tokens** | `tokens.{input,output,cache_read,cache_creation}` | summed `usage` across stages. Cache reads are most of the input and cost 10× less, so they are kept separate |
| **Wall-clock** | `agent_wall_s` | time spent in agent stages only (setup and grading excluded) |
| Turns | `num_turns` | summed agentic turns |
| Process | `review_verdict`, `fix_round`, `plan_subtasks`, per-stage `stages[]` | lets you ask, for example, "when the reviewer approved, how often was it wrong?" |
| Change size | `diff`, `touched_tests` | bigger diffs at equal pass rate means more churn |
| Integrity | `read_only_violations`, `leak_suspected`, `status` | runs to exclude or investigate |

`status` is `passed` / `failed` when grading ran normally, and `budget_exceeded` / `timeout` /
`agent_error` when the pipeline stopped early. Early-stopped runs are **still graded**, and they count
as fails if the tests fail. A config that needs more budget than it's given has, for this study, failed.

### Repetition and statistics

The same prompt gives different results run to run, so one run per task is an anecdote.

- **At least 3 reps per (task, config).** `--reps 3` is the default.
- **Interleaved order.** For each rep and task, A, B and C run back to back. API slowdowns or
  load spikes then hit all configs equally instead of all landing on whichever config ran last.
- **Paired analysis by task.** All configs see the same tasks, so compare them task by task. "C solved
  t04 3/3 where A solved 1/3" carries more signal than overall rates. The report shows a per-task
  pass grid (T-6 adds a paired bootstrap of the pass-rate difference, resampling tasks, not runs).
- **Wilson 95% intervals** on pass rates. They are honest at small n, where the textbook ±1.96·SE
  interval misbehaves.
- **Be honest about power.** With 25 tasks × 3 reps = 75 runs per config, a pass rate of about 60%
  has a 95% interval of roughly ±11 points. Differences under ~15 points will be "no clear
  difference". That is a valid result and the write-up should say so.

### The confound to address: more compute vs. better structure

B and C spend more tokens than A. If they win, is it the team, or just more attempts? Ticket T-8
adds config **A2**: two independent single-agent attempts, keeping the first whose *visible* tests
pass, at roughly B's spend. If B beats A2 at equal cost, the structure is doing the work. Another
cheap ablation is **D = A + Stop-hook test gate** (T-13): the Boxwatch hook pattern, with no second
agent.

---

## 4. Cost guardrails

Three layers, all in place now:

1. **Per-stage cap.** `--max-budget-usd` is set to whatever is left of the run's budget, so the
   stages share one cap (default `run_budget_usd: 2.00`). Claude Code enforces it and stops the stage.
   `--max-turns 40` and a 15-minute stage timeout catch loops that cost little per turn but never finish.
2. **Per-sweep cap.** `--max-total-usd` is **required** for any non-dry run. The runner stops starting
   new runs once cumulative spend reaches it. A run already in progress can overshoot by at most one
   run budget.
3. **Explicit go.** A paid run prints its plan and an estimate, and refuses to start without `--yes`.

Plus two **dry-run modes**, which never call the API:

- `python -m ate run --dry-run`: a fake CLI returns canned events (reviewer says CHANGES_NEEDED,
  planner returns two subtasks), so every branch of every pipeline runs. Worktrees, prompts, command
  lines, read-only checks, grading and result records are all real. The unchanged code fails the
  hidden tests, as it should.
- `--dry-run --oracle`: fake builders copy in the reference solution, so the pass path, diff stats
  and grading are exercised too. `scripts/check.py` runs this on every change.

### What a full run would cost (rough)

These are estimates. Replace them with measured numbers after the first smoke run (ticket T-1).
Assumptions: Sonnet 5.5 at $2 input / $10 output / $0.20 cache-read per million tokens; a small
task takes a builder about 10–20 turns, and most input is cache reads of a ~20–40k-token context.

| Stage | Guess per stage |
|---|---|
| A solve / builder | $0.15–0.40 |
| reviewer | $0.08–0.15 |
| planner | $0.08–0.15 |
| fix (about half the runs) | $0.10–0.25 |

| Config | Per run |
|---|---|
| A | ~$0.25 |
| B | ~$0.45 |
| C | ~$0.70 |
| **A+B+C, one task, one rep** | **~$1.40** |

| Sweep | Runs | Rough cost |
|---|---|---|
| Smoke: 1 task × A × 1 rep | 1 | ~$0.10–0.40 (capped at $0.50) |
| Pilot: 5 tasks × 3 configs × 3 reps | 45 | ~$20 (range $12–40) |
| Full: 25 tasks × 3 configs × 3 reps | 225 | ~$105 (range $60–200) |
| Full on Opus 5.5 ($4/$20) | 225 | roughly 2× that |

The estimate `ate run` prints before a paid sweep is cruder and deliberately high: it assumes
$0.20 per stage, that C always plans 3 subtasks, and that every fix round runs (about $2.00 per
task-rep instead of $1.40). T-1 replaces the $0.20 with a measured number.
The worst case if every run hits its $2 cap is $450 for the full sweep. That is why
`--max-total-usd` is required (for example `--max-total-usd 150`).

---

## 5. The write-up

The final README section and chart answer the question in one picture plus a table:

1. **Headline chart: pass rate vs. cost per run**, one point per config with Wilson error bars on
   pass rate and an interquartile range on cost. The cost-quality frontier is visible at a glance:
   is C up and to the right (better but pricier), or just to the right (pricier)?
2. **Per-task grid** (tasks × configs, cell = passes/3): where teams help (multi-file, subtle bugs)
   and where they only add cost (single-file fixes).
3. **Table**: pass rate (CI), partial credit, mean $/run, **$ per passed task**, median wall time,
   tokens, fix-round rate. "$ per passed task" is the number a team lead would budget with.
4. **Where the money goes**: stacked bar of C's spend by stage (plan / build / review / fix).
5. **Reviewer quality**: when the reviewer said APPROVE, how often did hidden tests pass? When
   it said CHANGES_NEEDED, did the fix round actually turn fails into passes?
6. **Caveats, stated plainly**: task count and power, one model, harness-orchestrated teams, the
   compute confound and what A2 showed, and the client-side cost estimate.

`python -m ate report results/*.jsonl` produces items 3 and part of 2 today (stdlib markdown).
The chart script is ticket T-7 (matplotlib, dev-only dependency).

---

## 6. Layout

```
ate/                 the runner (stdlib only): python -m ate {list,validate,run,report}
  __main__.py        CLI, cost guards, sweep loop
  pipeline.py        one run: worktree → stages → grade → record; dry-run fakes
  claude.py          builds the claude -p command, runs it, parses the result event
  workspace.py       seed repos, worktrees, read-only snapshot/restore
  grade.py           hidden tests via unittest
  results.py         record validation + JSONL append
  report.py          markdown summary with Wilson intervals
configs/
  defaults.json      model, budgets, tools: shared by all configs
  A.json B.json C.json   stage lists
  B/.claude/agents/  builder.md reviewer.md
  C/.claude/agents/  planner.md builder.md reviewer.md
  prompts/           stage prompt templates ($task_prompt, $findings, ...)
  schemas/           --json-schema bodies for verdict and plan
tasks/               t01-slugify, t02-ttl-cache (+ hidden tests and solutions)
docs/results.schema.json
results/             committed JSONL from real sweeps
scripts/check.py     compile + tests + validate + oracle dry run (no API calls)
```
