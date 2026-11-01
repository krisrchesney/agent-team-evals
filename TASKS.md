# agent-team-evals backlog

The shared board for every session. Statuses: Ready -> In progress -> Review -> Done.
A ticket owns the files it lists. Two tickets in progress must never own the same file.
Tickets marked **(user)** need the user's decision or use of their plan, so a session can't start them alone.

Template:

    ### T-<n>: <title>
    Status: Ready | Blocked | In progress (branch) | Review (branch) | Done
    Owns: <files>
    Blocked by: <ticket, "user", or "none">
    Why: <one or two lines>
    Done when:
    - [ ] <something a reviewer can check without asking anyone>

## Ready (independent: these can run as parallel sessions)

## Blocked

### T-1: Smoke run (user): one task, config A, one rep, on the subscription
Status: Done (smoke + calibration)
Owns: configs/defaults.json (`estimate_api_equiv_usd_per_stage` only); DESIGN.md §4 usage table
Blocked by: user. (1) Turn off "extra usage" in claude.ai settings. (2) Sign in the clean profile once:
`python -m ate auth` prints the command; it must then say OK. (3) Note the plan usage % right before,
and OK the run. Expected: roughly 1-3% of a usage window (a guess until measured), nothing billed.
Why: Every usage figure in DESIGN.md is a guess until one real run exists. The smoke run also checks
what the dry run can't: the clean profile really is clean (`isolation_flags` empty), `apiKeySource`
is "none", `--agents` + `--agent` work, `structured_output` appears in the stream-json result event,
and Windows quoting of `--allowedTools` is right.
Command: `python -m ate run --tasks t01 --configs A --reps 1 --run-cap 0.5 --max-total-api-equiv 0.5 --yes`
First attempt, sweep 20261029T163857Z (record moved to D:/ate-work/rejected/, transcript in D:/ate-work/sweeps/):
passed 11/11, 319,672 tokens (80,838 cache-creation, 236,912 cache-read, 1,914 output), 7 turns, 21 s.
Rejected as data, and found two harness bugs, both fixed since: (1) 4 claude.ai connectors (Gmail, Calendar,
Atlassian, Docs; 73 tools) were loaded, inflating context; now `ENABLE_CLAUDEAI_MCP_SERVERS=false` and
`--strict-mcp-config`; (2) the agent had no shell tool ("No such tool available: Bash"), so it could not run
tests; `PowerShell` is now offered too and a run whose init lists no shell tool stops as `harness_error`.
Second attempt, sweep 20261029T170026Z (record also in D:/ate-work/rejected/): passed 11/11 with the shell
fix working (agent ran unittest via PowerShell) and no MCP servers: 46,605 tokens (5,079 cache-creation,
39,695 cache-read, 1,823 output), 7 turns, 22 s, 7x fewer tokens than attempt 1. Rejected again: three
account-synced plugins (cowork-plugin-management, data, databricks; 75 skills) were loaded, and auto-memory
was live in the clean profile (a run could leave notes for the next). Fix: `--safe-mode` for subscription runs.
Third attempt, sweep 20261029T172613Z (kept in results/): passed 11/11, 44,017 tokens, 7 turns, 17.6 s,
`isolation_flags` and `leak_suspected` empty, apiKeySource none, PowerShell as the shell, no MCP, synced
plugins or memory. First accepted record.
Calibration, sweep 20261029T173012Z (t01+t02 x A,B,C, 1 rep): all six passed. `--safe-mode` hides `--agents`
roles (B and C first failed with "agent not found" before any model call), so roles are now appended with
`--append-system-prompt` from the same .claude/agents files; never-started stages are `harness_error`
(retryable). Tokens per run: A 65,528, B 107,367 (1.64x), C 131,071 (2.00x); see DESIGN section 4.
Done when:
- [x] One real record in results/ with non-zero tokens, `auth: subscription`, empty `leak_suspected` and `isolation_flags`
- [x] Usage recorded (DESIGN §4): tokens, turns, time, API-equivalent $; the plan bars are too coarse (1-point steps) to resolve one run
- [x] Then the calibration sweep (t01+t02 x A,B,C x 1 rep = 6 runs, user OK) confirms the reviewer returns a parsed verdict and the planner a plan
- [x] DESIGN §4 tables updated from measured numbers, with the sweep ids

### T-16: Pilot sweep (user): 5 tasks x A,B,C x 3 reps = 45 runs
Status: Done 2026-10-29 (started 17:09 local, 45 of 45 runs counted, sweep 20261029T220931Z; see README). Earlier: armed 15:53 local. Starts itself at 17:30 local (US Central) through a session background
task (id bpaatmwsh) running D:\ate-work\pilot-launch.ps1; log D:\ate-work\pilot-launch.log. It stops if the
app closes, the PC sleeps or the user logs out; it will not start if it wakes more than 2 h late.
Owns: results/<sweep>.jsonl (new); README.md results section; DESIGN.md section 4 pilot numbers
Blocked by: nothing once it has run; the user chose the 17:30 start (relayed 2026-10-29).
Why: First real pass-rate table, and the usage data that decides whether the full sweep fits.
Command: `powershell -File scripts\run_sweep.ps1 -Tasks "t01,t02,t03,t04,t05" -Reps 3`
(run cap 1.5 and sweep cap 15 API-equivalent dollars: runaway guards, about 3x the expected total, and a
run cap high enough that a long multi-file run is not cut off and counted as a failure).
Audit before running (done 2026-10-29): every hidden test in t03-t05 traces to a numbered requirement.
Done when:
- [x] 45 countable records, no `harness_error`/`rate_limited` left, `isolation_flags` and `leak_suspected` empty
- [x] `python -m ate report` table committed to README with the sweep id; usage per config in DESIGN section 4
- [x] Caveats written: 5 tasks, 3 reps, one model, wide intervals

### T-8: Tasks t06-t14 (second batch)
Status: Done 2026-10-29, merged to master: nine tasks written by three sessions, audited (every hidden test
traces to a numbered requirement) and probed with one run of config A each: 9 of 9 passed, so they do not
separate the configs. Next: a third, much harder batch (t15+), see the board.

### T-8d: Tasks t15-t18 (third batch, much harder)
Status: Done 2026-10-29, merged to master from branches ticket/T-9a-tasks, T-9b-tasks, T-9c-tasks (named before
the T-9 ticket number was taken). 25-36 requirements, 88-134 hidden tests each, audited. Probe: config A passed
4 of 4 (see DESIGN section 4), so they do not separate the configs either.

### T-17: Under-specified tasks t19-t21
Status: Done 2026-10-30, merged to master from ticket/T-17-underspec-tasks. Short prompts; rules live in the
starting repo, mapped per test in each task's AUDIT.md. t19-refunds (add an operation following conventions, 39
hidden tests), t20-vendor-import (new supplier format plus importer contract and config, 24), t21-statement-bugs
(two customer complaints, four root causes, 20). All validate; each t21 cause is caught on its own. Probe: config
A passed 3 of 3 (sweep 20261030T165840Z). Project stopped here by the user's choice; no more runs planned.

### T-9: Config A2: equal-compute baseline (best of 2 single agents)
Status: Done 2026-10-30 in T-18 (branch ticket/T-18-phase0): `best_of` config key, fresh worktree per try,
first try whose visible tests pass is graded, usage summed; record field `tries`. Dry-run tests cover both paths.

### T-10: Config C-auto: Claude orchestrates the team itself
Status: Ready (phase 2, optional)
Owns: configs/C-auto.json (new); configs/C-auto/.claude/agents/ (new)
Blocked by: none. Check first: `--safe-mode` hides `--agents`, so the lead may only reach the built-in
general-purpose subagent; the roles would have to go in the lead's prompt.
Why: Measures in-session subagent orchestration (one `claude -p` with a lead agent calling planner,
builder and reviewer), as opposed to harness-driven C.
Done when:
- [ ] Single stage, lead agent with the Agent tool; roles copied unchanged from configs/C
- [ ] Dry run passes; DESIGN §2 mentions it

### T-11: Config D: single agent + test gate
Status: Done 2026-10-30 in T-18: a harness stage (`"run": "visible_tests"`) runs the repo's own tests with no
model call, and one fix round (prompt gate_fix.md) runs only if they fail. Not a Stop hook: `--safe-mode`
turns hooks off.

### T-12: Parallel runs (`--jobs N`)
Status: Blocked
Owns: ate/__main__.py (sweep loop)
Blocked by: T-1 (need real rate-limit behaviour first)
Why: A full sweep is about 225 sequential runs. Parallel runs cut wall time; per-run wall-clock is unaffected.
Done when:
- [ ] Results are appended safely from several workers; `--max-total-api-equiv` is still respected
- [ ] Default stays 1

### T-13: Container isolation for agent runs
Status: Blocked
Owns: ate/sandbox.py (new); DESIGN.md §2 isolation paragraph
Blocked by: user (is Docker installed and OK to use?)
Why: Worktrees outside the repo stop accidental leaks, not a determined search of the disk.
Done when:
- [ ] Opt-in `--sandbox docker` mounts only the worktree; leak check still runs

### T-14: Subscription mode (built; real-run check is part of T-1)
Status: Done (code); verification rides on T-1
Clean profile via CLAUDE_CONFIG_DIR, scrubbed env (no ANTHROPIC_*/CLAUDE* vars), pre-flight
`claude auth status` check, apiKeySource and personal-CLAUDE.md canary checks, `rate_limited`
status that halts the sweep, `--resume`. Tests in tests/test_harness.py (TestSubscriptionSafety, TestResume).

### T-15: Publish (user): GitHub repo, CI, README results
Status: Blocked
Owns: .github/workflows/check.yml (new); README.md results section
Blocked by: user (create the public repo and push?) and a real sweep
Done when:
- [ ] CI runs `python scripts/check.py` (no API calls, no secrets)
- [ ] README results come only from committed results/*.jsonl, sweep id cited

### T-18: Phase 2 study, phase 0: setups and tools (no plan usage)
Status: Review (ticket/T-18-phase0)
Owns: ate/config.py, ate/pipeline.py, ate/grade.py, ate/__main__.py (estimate), configs/{A2,AS,D,B-hs,B-so}.json,
configs/prompts/{gate_fix,recheck}.md, scripts/{task_features,power}.py, docs/task_features.json, DESIGN.md 5b
Why: DESIGN section 5b. Configs for every question in the study, task measurements to chart results
against, and the sample size the main sweep needs.
Done when:
- [x] Per-stage `model` (haiku, sonnet, opus); `best_of` (A2); harness stage `visible_tests` (D); AS self-check
- [x] Subtest failures counted once per test in grading (the "passed 0" quirk)
- [x] `scripts/task_features.py --write` and `scripts/power.py`; DESIGN 5b has the plan and the power table
- [x] Dry-run tests for A2 (both paths), D (both paths), stage models; check.py passes; A, B, C commands unchanged

### T-19: Phase 1 task batch: tasks where one agent should fail sometimes
Status: Review (ticket/T-19-batch4). Done: t22-t41 (20 tasks). t22 here; t23-t41 by five parallel
Sonnet 5.5 writer sessions (branches ticket/T-19-implied, -large, -cross, -long, -clarify), reviewed and
merged 2026-10-31. Clarify-first t38-t41 use ask_user. In review, natural phrasings of 4 of 22 questions
fell through to the default answer, so keywords were added and the default now asks the agent to name
the decision it means. Keyword matching will still miss some phrasings: the report should count
default answers per run (questions[].matched == []) to separate matcher misses from not asking.
Owns: tasks/t22-* and up (new)
Why: The first study's tasks never made A fail. DESIGN 5b lists five kinds to build: rules only implied by
code, large repos, cross-module changes, clarify-first requests (needs T-23), long multi-step features.
Candidates (one folder each; independent, so they can be written in parallel sessions):
- Implied by code: t22-stock-holds (done); t23-flag-rollouts (new flag type; hashing and evaluation
  order only in existing types); t24-cli-export (new subcommand; exit codes, stderr format, --json shape
  shared by the others); t25-pipeline-plugin (new stage plugin; lifecycle and error wrapping in the base).
- Large repo (3,000+ lines, must search): t26-proration (one period rule computed in five places);
  t27-search-field (new indexed field through serializer, tokenizer, query parser, cache key);
  t28-config-rename (rename a setting with back-compat across a dozen modules); t29-hot-path (an
  O(n^2) path; hidden tests have a time budget).
- Cross-module: t30-multi-currency (single-currency ledger to multi-currency); t31-aware-times (naive
  to timezone-aware datetimes across a scheduler); t32-soft-delete (every query must skip deleted rows);
  t33-tenant-scope (tenant id through every read and write).
- Long multi-step: t34-migrations (ordering, rollback, checksums); t35-rate-limits (token bucket, sliding
  window, persistence, clock skew); t36-patch-apply (diff, unified format, fuzzy apply); t37-mini-sql
  (joins and GROUP BY over CSV tables).
- Clarify-first (need T-23): t38 to t41, ambiguous requests with a hidden answer sheet.
Done when:
- [x] About 20 candidates, each validating, with an AUDIT.md mapping every hidden test to a rule in the repo
  (20 done)
- [x] task_features.json regenerated

### T-20: Phase 1 screening (user): config A, Sonnet, 2 runs per candidate
Status: In progress. Batch 1 (sweep 20261101T051503Z, t22-t31): 15/20 passed; t22 0/2, t23 0/2,
t25 1/2, the rest 2/2. Batch 2 (sweep 20261101T113613Z, t32-t41): t32-t37 9/12 (t34 1/2, t37 0/2;
fair spec misses). t38-t41 0/8 is INVALID: ask_user connected but the harness prompt (solve.md) said
"Do not ask questions; nobody will answer", so no run asked. Fixed in 5f81d04 ($questions_rule; other
runs' prompts unchanged). t38-t41 need a rerun (8 runs) with the user's go.
Decision (user, 2026-11-01): t23 is dropped from the main study. Both its failures came from
test_to_dict expecting input order for ramp steps, a convention the repo shows only weakly. The task is
not changed after real results; it stays in tasks/ with this note.
Why: Go/no-go. Keep tasks A passes some of the time but not always. If none, the study ends there.

### T-21: Phase 2 main sweep (user)
Status: Blocked by T-20
Why: About 20 screened tasks x 5 runs x A, AS, D, A2, B (+ C on large-repo tasks). Run in batches across
usage windows with run_sweep.ps1; estimate before each batch.

### T-22: Phase 3 model matrix (user, Opus OK needed)
Status: Blocked by T-21
Why: A with Haiku and Opus, B-hs, B-so on a 10-task subset x 3 runs.

### T-23: Stand-in user for clarify-first tasks
Status: Done 2026-10-31 (ticket/T-23-askuser, merged into ticket/T-19-batch4). A task opts in with
`"ask_user": true` in task.json and an answers.json beside repo/. `--safe-mode` drops `--mcp-config`
(checked on the real CLI), so ask_user runs use `--setting-sources ""` and `--disable-slash-commands`
instead, and the isolation check also flags skills and slash commands. Every other command is unchanged.
Still to confirm on the first real ask_user run: the server connects, and no auto-memory carries over.
Owns: ate/askuser/ (new local stdio MCP server), configs/defaults.json (an `ask_user` tool option)
Why: Headless runs cannot ask questions. A tiny MCP tool answers from the task's hidden answers.json
(keyword match, no model call) and logs each question, so "asked the right question" is measurable.
Done when:
- [x] Passed with `--mcp-config` alongside `--strict-mcp-config`; the isolation check allows only this server
- [x] Questions and answers are recorded per run; dry-run test

### T-24: Report and charts for the phase 2 study
Status: Ready
Owns: ate/report.py, scripts/plot.py
Why: Tokens per passed run by config, pass rate against task features, and the "cheapest reliable setup"
map, from results JSONL only.

## In progress

## Review

## Done

### T-0: Design and scaffold
Status: Done
DESIGN.md, runner (`ate/`), configs A/B/C with roles, tasks t01-t02 with hidden tests and solutions,
results schema, dry-run and oracle modes, scripts/check.py, Stop hook, this backlog.

### T-2: Task t03: multi-file CSV report CLI
Status: Done. Merged to master 2026-10-29: t03-csv-report (4/28 hidden tests pass on the start code, 28/28 with the reference).

### T-3: Task t04: subtle bug hunt (interval merging)
Status: Done. Merged to master 2026-10-29: t04-interval-merge (4/10 -> 10/10).

### T-4: Task t05: spec with an ambiguity (config file + env overrides)
Status: Done. Merged to master 2026-10-29: t05-env-config (0/18 -> 18/18).

### T-5: Paired comparison in the report
Status: Done 2026-10-29, merged to master: paired comparison in the report (bootstrap over tasks).

### T-6: Chart script for the write-up
Status: Done 2026-10-29, merged to master: scripts/plot.py and the three pilot charts in docs/figures/ (used in the README).

### T-7: Per-stage overrides in the pipeline
Status: Done 2026-10-29, merged to master: per-stage overrides (tools, allowed_tools, settings) with a golden-command test that A, B and C are unchanged.
