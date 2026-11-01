# Study 2: main sweep on the screened tasks (interim)

Status: interim working report. Sonnet 5.5 only, 11 tasks, 5 runs per task for each setup.

**No setup passed more tasks than a single agent.** The sample is too small to show that a team cannot
help, and many failures in the first sweep come from tests that are themselves debatable. Self-check (AS) and
the team (B) used about 1.4 to 1.6 times the tokens of a single agent. On tasks with open product decisions,
what separated passes from fails was whether the agent asked about every decision, not which setup it ran in.

## What ran

Sweeps `20261101T145209Z`, `145229Z`, `145249Z`, `145309Z`, `145330Z`, `145350Z` and `145410Z`: tasks t22,
t25, t34, t37, t38, t39 and t40, by setups A, AS, D, A2 and B, by 5 runs, on 2026-11-01. That is 175 runs and
33,926,783 tokens. One process per task ran at once, so time figures are not comparable and are left out.

Four t37 r5 runs (AS, D, A2, B) hit the plan's 5-hour limit, so they are void. The harness recorded them as
`agent_error` because its limit detector missed the wording of that message; this is now fixed and tested. They
were redone in sweep `20261101T171935Z` (1,329,304 tokens, all four failed), and the tables below use the redo.

| Setup | What it does |
|---|---|
| A | One agent |
| AS | One agent, then a fresh agent re-reads the request and fixes what it finds |
| D | One agent, plus one fix round if the visible tests fail |
| A2 | Up to two independent attempts; a second only if the first fails the visible tests |
| B | Builder, reviewer, and one fix round if the reviewer asks for changes |

## Results

Passes as recorded (every hidden test passes):

| Task | A | AS | D | A2 | B |
|---|---|---|---|---|---|
| t22-stock-holds | 0/5 | 1/5 | 0/5 | 0/5 | 0/5 |
| t25-pipeline-plugin | 3/5 | 3/5 | 2/5 | 3/5 | 3/5 |
| t34-migrations | 4/5 | 3/5 | 5/5 | 3/5 | 3/5 |
| t37-mini-sql | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 |
| t38-refund-policy | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 |
| t39-merge-contacts | 3/5 | 0/5 | 1/5 | 4/5 | 2/5 |
| t40-shift-swap | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 |
| **All** | **10/35** | **7/35** | **8/35** | **10/35** | **8/35** |
| Tokens per run | 160,959 | 265,188 | 152,437 | 161,955 | 264,897 |
| Tokens per pass | 563,358 | 1,325,944 | 666,913 | 566,843 | 1,158,927 |

Compared with A on the same task and run number, where only one of the pair passed:

| Setup | Setup only | A only | Sign test p |
|---|---|---|---|
| AS | 2 | 5 | 0.45 |
| D | 2 | 4 | 0.69 |
| A2 | 3 | 3 | 1.00 |
| B | 1 | 3 | 0.62 |

None of these differences can be told apart from chance.

## The second score: without debatable tests

Auditing the failures found tests whose rule the repo does not settle. Tasks stay unchanged, because real
results exist. This second score drops those tests. **I chose them after seeing the results, so it is a
sensitivity check, not the primary result.**

| Test | Fails | Why it is debatable |
|---|---|---|
| t22 `test_capture_event` | 20/25 | Allows extra events but requires `hold.captured` first. Existing operations emit one event, so no order is shown, and the prompt calls a capture a shipment. |
| t22 `test_release`, `test_create_event` | 8/25 each | Require event data to be exactly `{"hold": view}`. Stock events in the same repo also carry a second record, so including the item is a reasonable reading. |
| t38 `test_r1_refund_view` | 25/25 | Requires `created_at`, `updated_at` and `version`. The repo has two shapes: charges have them, ledger entries have only `at`. A refund could follow either. |
| t38 `test_r1_reason_has_a_default`, `test_r2_ledger_ref_is_the_reason` | 23/25, 22/25 | Require a non-empty default reason. The only source is one analogy (`description` defaults to `"charge"`), and the answer sheet has no entry for it. |
| t40 `test_accept_event` | 25/25 | Requires the accepted event to carry the changed shift. The prompt and answer sheet don't say so, and every existing event in the repo carries one record. |

| | A | AS | D | A2 | B |
|---|---|---|---|---|---|
| All, without debatable tests | 22/35 | 16/35 | 21/35 | 24/35 | 17/35 |
| Setup only / A only | | 3 / 9 | 4 / 5 | 6 / 4 | 2 / 7 |
| Sign test p | | 0.15 | 1.00 | 0.75 | 0.18 |

The conclusion is the same under both scores: no setup beats A, and AS and B sit lower without reaching
significance.

Failures I judged fair: t25 (`test_flushing_empties_the_stage`), t34 (`test_bad_arguments`), t39
(`test_unknown_contacts`, `test_event`), t38's refund window (decision never asked about) and t37. t37's
`SELECT SUM(*)` and `SelectItem.text` rules are both written in its spec, and 0 of 25 runs passed.

## What the setups did

- **D and A2 never acted.** D's fix round never ran and A2 never made a second attempt, because the visible
  tests passed every time. On these tasks both are the same as A, so they say nothing about test gates or
  extra attempts. They do show the noise: t39 scored 3/5, 1/5 and 4/5 across three effectively identical setups.
- **The reviewer did not rescue a run.** B's reviewer approved 27 runs and 19 of those failed the hidden tests.
  It asked for changes in 7, and all 7 still failed after the fix round. One B run was the limit-cut run above;
  its redo was approved and also failed.
  This uses the recorded score, so some of those failures rest on debatable tests.
- **Missing rules are hard to review for.** Most failures are rules that neither the visible tests nor the
  request state, so a second agent reading the same request has nothing to check them against.

## New tasks t42 to t49

Screening: A, 2 runs each, 2,198,945 tokens across 8 sweeps from `20261101T163...`. The same tests failed in
both runs of every failing task.

| Task | Passed | Why | Decision |
|---|---|---|---|
| t42-book-holds | 0/2 | Never asked about `limit` or `overdue` | Keep |
| t43-vouchers | 0/2 | Never asked about `one_per_order` | Keep |
| t44-expense-approvals | 0/2 | Never asked about `second` or `window` | Keep |
| t45-recurring-appointments | 0/2 | Never asked about `one_series` | Keep |
| t46-library-reservations | 0/2 | A member who already holds a book cannot reserve it: not in the prompt, and the audit's source does not state it | Drop: debatable |
| t48-order-points | 0/2 | Event must nest its fields under `points`, while the prompt reads as flat fields | Drop: debatable |
| t47-lint-rule | 2/2 | | Drop: passes |
| t49-tiered-meter | 2/2 | | Drop: passes |

t42 to t45 fail for the intended reason, a decision the agent did not ask about. Across the study, rules shown
only by code keep producing debatable tests (t22, t23, t46, t48).

## Clarify sweep: t42 to t45

Sweeps `20261101T171855Z`, `171905Z`, `171915Z` and `171925Z`: 60 runs, setups A, AS and B, 5 runs each. With the
t37 redo, the session used 15,065,907 tokens. There were no isolation flags and no default answers.

| Task | A | AS | B |
|---|---|---|---|
| t42-book-holds | 0/5 | 0/5 | 0/5 |
| t43-vouchers | 5/5 | 4/5 | 3/5 |
| t44-expense-approvals | 0/5 | 0/5 | 0/5 |
| t45-recurring-appointments | 0/5 | 0/5 | 0/5 |
| **All** | **5/20** | **4/20** | **3/20** |
| Tokens per run | 175,922 | 267,348 | 243,558 |
| Decisions covered, of 5 on average | 3.50 | 3.60 | 3.65 |
| Questions per run | 1.00 | 1.35 | 1.10 |

Against A on the same task and run: AS passed where A failed 0 times and A passed where AS failed once (p=1.00);
B 0 and 2 (p=0.50).

- **Asking every question decided the result.** Of 60 runs, 11 covered every decision and all 11 passed. The other
  49 had 1 pass. **All 11 were on t43**, so this rests on one task; within t43 it is 11/11 against 1/4.
- **Screening misjudged t43.** It failed 2 of 2 in screening, then A passed 5 of 5. Two runs cannot tell a task A
  fails from one it sometimes fails.
- **Extra agents barely raised coverage.** AS's recheck agent asked 7 more questions across 20 runs. B's reviewer
  asked none. Average coverage moved from 3.50 to 3.60 and 3.65 of 5.
- **The reviewer rarely flagged anything.** It approved 18 of 20, and 15 of those failed. The 2 runs where it asked
  for changes also failed.

## Limits

- 11 tasks at 5 runs per cell, with D and A2 on only 7. The earlier simulation wanted about 20 tasks to detect a
  20-point gap.
- Sonnet 5.5 only. The Haiku and Opus part of the study has not run.
- The second score and the list of debatable tests are one reviewer's judgement, made after the results.
- Task writers were Sonnet agents, and the debatable tests are partly a flaw in those tasks.
- Sign tests are unadjusted for comparing several setups, which only makes them more generous.
- Repeated runs of one task are not independent evidence about other tasks.
- The reference answer sheets match by keyword, so a question can only earn an answer it happens to match.

## Harness fixes from this review

- The limit detector now recognises "You've hit your 5-hour limit".
- `hidden_tests.txt` now keeps the whole test output. It kept only the last 1,500 characters, though recorded
  pass and fail counts were never affected. `scripts/rescore_main_sweep.py` regraded the kept worktrees, without
  any model calls, and every count matched the record.

Reproduce: `python scripts/rescore_main_sweep.py <sweeps folder> results/20261101T145*.jsonl results/20261101T171935Z.jsonl`
