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

### T-5: Paired comparison in the report
Status: Ready
Owns: ate/report.py; tests/test_report.py (new)
Blocked by: none
Why: Configs see the same tasks, so comparing them task by task is more powerful than overall rates.
Done when:
- [ ] `report` prints, for each pair (B-A, C-A, C-B), the pass-rate difference with a 95% paired bootstrap CI that resamples tasks, not runs (fixed seed)
- [ ] Also prints tokens per passed task with the same CI method
- [ ] Unit tests on a hand-made record list with a known answer; stdlib only

### T-6: Chart script for the write-up
Status: Ready
Owns: scripts/plot.py (new); docs/figures/ (new)
Blocked by: none
Why: DESIGN §5: pass rate vs usage (tokens) frontier, per-task grid, C's tokens by stage.
Done when:
- [ ] `python scripts/plot.py results/<sweep>.jsonl` writes 3 PNGs to docs/figures/
- [ ] matplotlib imported only in this script; a clear message if it isn't installed
- [ ] Works on the dry-run oracle output; dry-run charts carry a "DRY RUN" watermark

### T-7: Per-stage overrides in the pipeline
Status: Ready
Owns: ate/claude.py (StageSpec, build_command); ate/pipeline.py (only the StageSpec construction block in run_one); tests/test_overrides.py (new)
Blocked by: none
Why: T-10 (C-auto) needs a stage whose tools include `Agent`, and T-11 (config D) needs a
per-config `--settings` file. Both are small additions to how a stage's command is built.
Done when:
- [ ] A stage in configs/*.json may set `tools`, `allowed_tools` and `settings` (a path under configs/); defaults still apply otherwise
- [ ] The fairness test still holds: A/B/C produce the same commands as before (assert it)
- [ ] check.py passes

## Blocked

### T-1: Smoke run (user): one task, config A, one rep, on the subscription
Status: Blocked
Owns: configs/defaults.json (`estimate_api_equiv_usd_per_stage` only); DESIGN.md §4 usage table
Blocked by: user. (1) Turn off "extra usage" in claude.ai settings. (2) Sign in the clean profile once:
`python -m ate auth` prints the command; it must then say OK. (3) Note the plan usage % right before,
and OK the run. Expected: roughly 1-3% of a usage window (a guess until measured), nothing billed.
Why: Every usage figure in DESIGN.md is a guess until one real run exists. The smoke run also checks
what the dry run can't: the clean profile really is clean (`isolation_flags` empty), `apiKeySource`
is "none", `--agents` + `--agent` work, `structured_output` appears in the stream-json result event,
and Windows quoting of `--allowedTools` is right.
Command: `python -m ate run --tasks t01 --configs A --reps 1 --run-cap 0.5 --max-total-api-equiv 0.5 --yes`
Done when:
- [ ] One real record in results/ with non-zero tokens, `auth: subscription`, empty `leak_suspected` and `isolation_flags`
- [ ] Usage % before/after recorded next to the run's tokens, turns, time and API-equivalent $ (DESIGN §4)
- [ ] Then the calibration sweep (t01+t02 x A,B,C x 1 rep = 6 runs, user OK) confirms the reviewer returns a parsed verdict and the planner a plan
- [ ] DESIGN §4 tables updated from measured numbers, with the sweep ids

### T-8: Tasks t06-t15 (second batch)
Status: Blocked
Owns: tasks/t06-*/ ... tasks/t15-*/ (split into 2-3 tickets by the planner when unblocked)
Blocked by: T-1 (calibrate difficulty: if A passes everything, the tasks are too easy to separate configs)
Why: 5 tasks can't separate configs. DESIGN §3 needs 20-30.
Done when:
- [ ] Mix per DESIGN §1 categories; each passes `validate`

### T-9: Config A2: equal-compute baseline (best of 2 single agents)
Status: Blocked
Owns: configs/A2.json (new); ate/pipeline.py (`run_one` loop only)
Blocked by: T-7 (both touch pipeline.py)
Why: Separates "more usage" from "better structure" (DESIGN §3). Two independent A attempts,
keep the first whose visible tests pass.
Done when:
- [ ] Each attempt gets a fresh worktree; usage is summed over both attempts
- [ ] Dry-run oracle passes; check.py passes

### T-10: Config C-auto: Claude orchestrates the team itself
Status: Blocked
Owns: configs/C-auto.json (new); configs/C-auto/.claude/agents/ (new)
Blocked by: T-7
Why: Measures in-session subagent orchestration (one `claude -p` with a lead agent calling planner,
builder and reviewer), as opposed to harness-driven C.
Done when:
- [ ] Single stage, lead agent with the Agent tool; roles copied unchanged from configs/C
- [ ] Dry run passes; DESIGN §2 mentions it

### T-11: Config D: single agent + Stop-hook test gate
Status: Blocked
Owns: configs/D.json (new); configs/D/ (new: settings + hook script)
Blocked by: T-7
Why: The Boxwatch hook pattern without a second agent. A cheap alternative to a reviewer.
Done when:
- [ ] The hook runs the visible tests (never the hidden ones) and blocks stopping once
- [ ] Dry run passes

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
