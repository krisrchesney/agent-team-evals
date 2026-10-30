# agent-team-evals: design

**Question.** On the same set of coding tasks, does a team of Claude agents beat a single agent?
"Beat" here covers three things: **pass rate** on tests the agents never saw, **usage** (tokens,
turns), and **wall-clock time**. Runs use a Claude subscription, so nothing is billed per token and
usage is the honest unit. Dollars appear only as an "API-equivalent" yardstick for comparing configs,
never as a charge.

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
| Bug fix + small feature | t01 slugify (done) | Single file. Teams should add usage and little value; a good control. |
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
  --max-budget-usd <remaining run budget>   # runaway-loop cap (API-equivalent units) for this stage
  --permission-mode acceptEdits             # can edit files without asking
  --permission-prompts none                 # nobody is there to approve, so deny (don't hang)
  --tools Bash,Read,Edit,Write,Glob,Grep    # which tools exist (read-only stages drop Edit/Write)
  --allowedTools "Read,Edit,...,Bash(python -m unittest *),Bash(git diff *)"   # which run without asking
  --no-session-persistence                  # don't save the session to disk
  --agents <run>/agents.json --agent reviewer   # B and C: which role this stage plays
  --json-schema '<schema>'                  # reviewer and planner: structured output
```

run with a scrubbed environment: every `ANTHROPIC_*` / `CLAUDE*` variable removed, then
`CLAUDE_CONFIG_DIR=D:/ate-work/claude-config` (a clean, subscription-only profile).

**Why stream-json and not plain json?** `--output-format json` prints only the final result object
(`total_cost_usd`, `usage`, `modelUsage`, `num_turns`, `duration_ms`, `subtype`, `result`,
`structured_output`). `stream-json` ends with **that same object**, and before it we also get the
whole transcript. We save it per stage, so when C loses to A on a task you can read why. The
harness reads only the last `type: "result"` line for the numbers.

**Auth: your Claude subscription, no extra spend.** `"auth": "subscription"` in
`configs/defaults.json` (the default). Runs count against your Pro/Max plan's usage limits, and
nothing is billed per token. Getting there needed three safeguards:

1. **A clean profile.** Without isolation, `claude -p` loads your personal `~/.claude` setup: your
   CLAUDE.md (which tells Claude to print the CST time first), plugins, hooks and memory. That
   would contaminate the benchmark. `CLAUDE_CONFIG_DIR` points each run at its own config folder,
   which holds only a login you create once (`python -m ate auth` prints the command). Per the
   Claude Code docs, settings, plugins, history and `.credentials.json` all live under that folder.
2. **No API key can sneak in.** In `-p` mode Claude Code prefers `ANTHROPIC_AUTH_TOKEN`, then
   `ANTHROPIC_API_KEY`, over a subscription login. So the harness strips every `ANTHROPIC_*` and
   `CLAUDE*` variable from the run's environment. That also drops what a parent Claude session
   exports: this desktop app sets `CLAUDE_CODE_SIMPLE` (which forces bare mode) and
   `ANTHROPIC_BASE_URL`.
3. **Checked before and during the run.** Before a sweep, `claude auth status` on the clean
   profile must report a subscription login, or the runner refuses to start. During a sweep, a
   stage that reports any API-key source stops the sweep with status `auth_error`. A reply that
   starts with your CST-timestamp rule, or a startup event listing plugins or MCP servers, stops
   it too (`isolation_flags`).

**The one setting the harness can't see: extra usage.** Pro/Max plans can let you keep working past
your limits at API rates. Turn it off in claude.ai settings before any sweep. Then a limit just
stops the run, and the harness records `rate_limited` and halts the sweep. `ate run --resume
<sweep>` continues it in the next usage window. Rate-limited runs are re-run, never counted as fails.

**What `api_equiv_usd` means on a subscription.** Usage is the primary measure: tokens (in, out,
cache), turns and wall time. Claude Code also reports `total_cost_usd`, what the run would have cost
at API prices; we store it as `api_equiv_usd`. Nobody is billed that amount. It is a handy single
number for comparing configs ("C used 2.8× A's tokens") and for sizing a usage window.
`--max-budget-usd` and `--max-total-api-equiv` count in the same units, which makes them runaway-loop
guards, not spending limits.

`"auth": "api_key"` exists for completeness (adds `--bare`, uses `ANTHROPIC_API_KEY`, billed per token). Do not use it; see CLAUDE.md.

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

That gives exactly "one round of fixes", and every token is attributed to a named stage, so you can
say, for example, "the reviewer used 18% of C's tokens". An in-session variant (C-auto) is ticket
T-10, as a separate config, because how well Claude orchestrates subagents is its own question.

The fix round is a **fresh** builder process. It receives the task, the reviewer's findings and the
working tree as the reviewer saw it. It does not `--resume` the build session, because resuming
reports the conversation's cumulative usage and would blur the per-stage accounting. C's builders run
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

### Per-stage overrides (for future configs)

A stage in `configs/<id>.json` may set three optional keys; everything not set falls back to
`configs/defaults.json`: `tools` (a comma string that replaces the tool list), `allowed_tools` (a list that
replaces the pre-approved tools) and `settings` (a JSON file inside `configs/`, passed as `--settings`).
This is how a later config can give a lead agent the `Agent` tool, or add a Stop-hook gate to a single
agent, without touching the code. Guard rails: unknown stage keys are an error, a settings file must live
inside `configs/` and may not set auth, model, plugins, MCP servers or `bypassPermissions` (or any
`ANTHROPIC_*`, `CLAUDE_*`, `AWS_*` environment variable), and `--safe-mode`, `--strict-mcp-config` and the
subscription checks are applied after the overrides, so a stage cannot switch them off. A, B and C use no
overrides, and `tests/golden_commands.json` (generated before this feature existed) plus a test prove their
commands are byte-for-byte unchanged. One thing to check when a config first uses `settings`: whether the
CLI honours `--settings` together with `--safe-mode`.

---

## 3. Metrics

One JSONL record per (task, config, repetition). The schema is `docs/results.schema.json`, and
`ate/results.py` validates every record before writing it.

| Metric | Field | How it's measured |
|---|---|---|
| **Pass** (headline) | `passed` | every hidden test passes |
| Partial credit | `tests.passed / tests.total` | shows "almost" vs "nowhere", which pass/fail hides |
| **Tokens** (usage) | `tokens.{input,output,cache_read,cache_creation}` | summed `usage` across stages, subagents included. Cache reads are most of the input and count for far less, so the four kinds are kept apart |
| **Turns** (usage) | `num_turns` | summed agentic turns |
| **Wall-clock** (usage) | `agent_wall_s` | time spent in agent stages only (setup and grading excluded) |
| API-equivalent $ | `api_equiv_usd` | sum of each stage's `total_cost_usd`, Claude Code's estimate at API prices. A yardstick that folds the token kinds into one number; **not a charge** |
| Process | `review_verdict`, `fix_round`, `plan_subtasks`, per-stage `stages[]` | lets you ask, for example, "when the reviewer approved, how often was it wrong?" |
| Change size | `diff`, `touched_tests` | bigger diffs at equal pass rate means more churn |
| Integrity | `read_only_violations`, `leak_suspected`, `status` | runs to exclude or investigate |

`status` is `passed` / `failed` when grading ran normally, and `cap_exceeded` / `timeout` /
`agent_error` when the pipeline stopped early. Early-stopped runs are **still graded**, and they count
as fails if the tests fail. A config that needs more than the runaway-loop cap has, for this study, failed.

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

B and C use more tokens than A. If they win, is it the team, or just more attempts? Ticket T-8
adds config **A2**: two independent single-agent attempts, keeping the first whose *visible* tests
pass, at roughly B's token usage. If B beats A2 at equal usage, the structure is doing the work. Another
cheap ablation is **D = A + Stop-hook test gate** (T-13): the Boxwatch hook pattern, with no second
agent.

---

## 4. Usage guardrails

The subscription is never billed per token, so the guardrails protect two things: your plan's usage
window, and against loops that run away. Three layers, all in place now:

1. **Per-run cap (runaway-loop protection).** `--max-budget-usd` is set to whatever is left of the
   run's cap, so the stages share it (default `run_cap_api_equiv_usd: 2.00`). The cap is in
   API-equivalent units because that is the only unit Claude Code can count in; it is not a spending
   limit. `--max-turns 40` and a 15-minute stage timeout catch loops that use little per turn but
   never finish.
2. **Per-sweep cap.** `--max-total-api-equiv` is **required** for any real run. The runner stops starting
   new runs once cumulative API-equivalent usage reaches it. A run already in progress can overshoot by
   at most one run cap.
3. **Explicit go, and a clean stop at your limit.** A real run checks the subscription login, prints
   its plan and estimate, and refuses to start without `--yes`. It halts at the first usage-limit hit
   (`rate_limited`) and continues with `--resume`.

Plus two **dry-run modes**, which never call the API and use no plan usage:

- `python -m ate run --dry-run`: a fake CLI returns canned events (reviewer says CHANGES_NEEDED,
  planner returns two subtasks), so every branch of every pipeline runs. Worktrees, prompts, command
  lines, read-only checks, grading and result records are all real. The unchanged code fails the
  hidden tests, as it should.
- `--dry-run --oracle`: fake builders copy in the reference solution, so the pass path, diff stats
  and grading are exercised too. `scripts/check.py` runs this on every change.

### How much of the plan a sweep will use (not yet measured)

Nothing has run yet, so there is no measured token count and no measured share of a usage window.
The smoke and calibration runs (ticket T-1) produce those, with you noting the usage bar on
claude.ai before and after each:

| Step | Runs | What it measures |
|---|---|---|
| Smoke: t01 × A × 1 | 1 | % of the usage window for one run; tokens, turns, time; whether the clean profile is clean |
| Calibration: t01+t02 × A,B,C × 1 | 6 | usage per config, so the ratios below become measured numbers |
| Pilot: 5 tasks × A,B,C × 3 | 45 | first real pass-rate table; usage windows needed for the full sweep |
| Full: 25 tasks × A,B,C × 3 | 225 | the write-up; likely several windows, run while you are away |

**First measurement** (smoke run, sweep `20261029T172613Z`, config A on t01, Sonnet 5.5): passed 11/11,
44,017 tokens (4,472 cache-creation, 37,634 cache-read, 1,903 output, 8 fresh input), 7 turns, 17.6 s,
about $0.04 API-equivalent. The shell tool was PowerShell, and the startup event listed no MCP servers, only
the CLI's three built-in plugins, no account-synced plugins and no auto-memory. This is one run of the
easiest task, so it fixes the order of magnitude and nothing more. The two rejected earlier attempts
(connectors and synced plugins loaded) used 319,672 and 46,605 tokens, which shows how much of a run's usage
isolation controls. On the plan's bars: the weekly bar moved about 1 point across the first two attempts
(about 370k tokens) and the session bar moved 1 point for the first one. At 1-point resolution that is as
precise as the bars get, so tokens, not bar percentages, are the unit to compare.

**Calibration** (sweep `20261029T173012Z`: t01 and t02, A/B/C, one run each, Sonnet 5.5; all six passed):

| Config | tokens / run | turns | median wall | API-equiv $ | vs A (tokens) |
|---|---|---|---|---|---|
| A single agent | 65,528 | 9.0 | 25.0 s | 0.052 | 1.00× |
| B builder + reviewer | 107,367 | 14.5 | 39.3 s | 0.123 | 1.64× |
| C planner + builder + reviewer | 131,071 | 18.0 | 51.2 s | 0.140 | 2.00× |

Two runs per config on the two easiest tasks, so these ratios are a first estimate, not a finding. What
the six runs did settle: roles reach the CLI through `--append-system-prompt` and the reviewer and planner
return valid `structured_output`; no read-only violations, leaks or isolation flags; the planner chose a
single subtask on both easy tasks; on t02 the reviewer asked for changes and the fix round ran (B), which
is the only time a fix round happened. Per stage, a builder used about 44-62k tokens, a reviewer about
22-47k and a planner about 45k, which is why B and C cost 1.6-2× A rather than 2-3×.

**Pilot** (sweep `20261029T220931Z`, 45 runs, all counted): 5,726,145 tokens, 667 turns, 2,118 s of agent time,
about 35 minutes of wall time. Per run: A 70,947 tokens, B 114,189 (1.61x), C 196,607 (2.77x). That is
a little above the calibration ratios (1.64x and 2.00x for C), because t03 is much heavier for C
(374k tokens per run against 123k for A). The sweep ran with a run cap of 1.5 and a sweep cap of 15
API-equivalent dollars; no run came near either. Averaged over configs the pilot used about 127k tokens
per run, against the 100k planned. A full 225-run sweep at that rate is about 28.6M tokens.

**Difficulty probes** (config A, one run per task, Sonnet 5.5, all passed): t06-t14, sweeps `20261030T015600Z`,
`20261030T015846Z`, `20261030T020045Z`: 854,488 tokens, 115 turns, 351 s of agent time (about 95k tokens per run).
t15-t18, sweeps `20261030T023845Z`, `20261030T024137Z`, `20261030T024402Z`: 1,035,437 tokens, 131 turns, 376 s
(about 259k tokens per run; t17 alone used 410k). Larger tasks cost a single agent more but did not make it fail.
Haiku 5.5 (`--model haiku`), t15-t18 and t12, sweep `20261030T044006Z`: 5 of 5 passed, 3,149,064 tokens, 142 turns,
863 s. Per task: t15 754,257, t16 562,097, t17 932,603, t18 824,512, t12 75,595 tokens. That is about 3x Sonnet's tokens
on t15-t18 (3,073,469 against 1,035,437) in about the same number of turns (132 against 131), so more tokens per turn.
Under-specified t19-t21 (Sonnet 5.5), sweep `20261030T165840Z`: 3 of 3 passed, 318,037 tokens, 36 turns, 112 s. Per
task: t19 128,561, t20 90,160, t21 99,316 tokens.

Planning figure used before the pilot (45 runs = 5 tasks × A,B,C × 3 reps): about 100k tokens per run averaged
over configs, so roughly 4.5M tokens, more if t03 (multi-file) pushes runs up. A full sweep (225 runs) is
about 23M. The plan's bars can't resolve a 100k-token run, so after each chunk of a sweep the bar is a
rough check only. If the pilot would pass about a quarter of a usage window, it is split across windows
(fewer reps first, never fewer configs).

The estimate `ate run` prints is deliberately crude and high: about $0.20 API-equivalent per stage,
C always planning 3 subtasks, every fix round running. T-1 replaces the $0.20 with a measured number.

---

## 5. The write-up

The final README section and chart answer the question in one picture plus a table:

1. **Headline chart: pass rate vs. usage per run**, one point per config, with Wilson error bars on
   pass rate and an interquartile range on tokens (the x-axis). The pass-rate-versus-usage frontier is
   visible at a glance: is C up and to the right (better but heavier), or just to the right (heavier)?
2. **Per-task grid** (tasks × configs, cell = passes/3): where teams help (multi-file, subtle bugs)
   and where they only add usage (single-file fixes).
3. **Table**: pass rate (CI), partial credit, tokens / run, output tokens / run, **tokens per passed
   task**, turns, median wall time, fix-round rate, with API-equivalent $ / run as the last column.
   "Tokens per passed task" is the number to read for efficiency.
4. **Where the usage goes**: stacked bar of C's tokens by stage (plan / build / review / fix).
5. **Reviewer quality**: when the reviewer said APPROVE, how often did hidden tests pass? When
   it said CHANGES_NEEDED, did the fix round actually turn fails into passes?
6. **Caveats, stated plainly**: task count and power, one model, harness-orchestrated teams, the
   usage confound and what A2 showed, and that API-equivalent dollars are an estimate, not a charge.

`python -m ate report results/*.jsonl` produces items 3 and part of 2 today (stdlib markdown).
The chart script is ticket T-7 (matplotlib, dev-only dependency).

---

## 6. Layout

```
ate/                 the runner (stdlib only): python -m ate {list,validate,run,report}
  __main__.py        CLI, usage caps, sweep loop
  pipeline.py        one run: worktree → stages → grade → record; dry-run fakes
  claude.py          builds the claude -p command, runs it, parses the result event
  workspace.py       seed repos, worktrees, read-only snapshot/restore
  grade.py           hidden tests via unittest
  results.py         record validation + JSONL append
  report.py          markdown summary with Wilson intervals
configs/
  defaults.json      model, runaway-loop caps, tools: shared by all configs
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
