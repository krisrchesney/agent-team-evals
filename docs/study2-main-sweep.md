# Study 2: main sweep on the screened tasks (interim)

Status: interim, not for publication. Sonnet 5.5 only, 7 tasks, 5 runs per task for each setup.

**No setup passed more tasks than a single agent.** The sample is too small to show that a team cannot
help, and many of the failures come from tests that are themselves debatable. Self-check (AS) and the team
(B) each used about 1.6 times the tokens of a single agent.

## What ran

Sweeps `20261101T145209Z`, `145229Z`, `145249Z`, `145309Z`, `145330Z`, `145350Z` and `145410Z`: tasks t22,
t25, t34, t37, t38, t39 and t40, by setups A, AS, D, A2 and B, by 5 runs, on 2026-11-01. That is 175 runs and
33,926,783 tokens. One process per task ran at once, so time figures are not comparable and are left out.

Four t37 r5 runs (AS, D, A2, B) hit the plan's 5-hour limit. They are void and excluded, leaving 171 runs. The
harness recorded them as `agent_error` because its limit detector missed the wording of that message; this is
now fixed and tested.

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
| t37-mini-sql | 0/5 | 0/4 | 0/4 | 0/4 | 0/4 |
| t38-refund-policy | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 |
| t39-merge-contacts | 3/5 | 0/5 | 1/5 | 4/5 | 2/5 |
| t40-shift-swap | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 |
| **All** | **10/35** | **7/34** | **8/34** | **10/34** | **8/34** |
| Tokens per run | 160,959 | 260,859 | 150,349 | 159,685 | 259,324 |
| Tokens per pass | 563,358 | 1,267,032 | 638,986 | 542,931 | 1,102,128 |

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
| All, without debatable tests | 22/35 | 16/34 | 21/34 | 24/34 | 17/34 |
| Setup only / A only | | 3 / 9 | 4 / 5 | 6 / 4 | 2 / 7 |
| Sign test p | | 0.15 | 1.00 | 0.75 | 0.18 |

The conclusion is the same under both scores: no setup beats A, and AS and B sit lower without reaching
significance.

Failures I judged fair: t25 (`test_flushing_empties_the_stage`), t34 (`test_bad_arguments`), t39
(`test_unknown_contacts`, `test_event`), t38's refund window (decision never asked about) and t37. t37's
`SELECT SUM(*)` and `SelectItem.text` rules are both written in its spec, and 0 of 21 runs passed.

## What the setups did

- **D and A2 never acted.** D's fix round never ran and A2 never made a second attempt, because the visible
  tests passed every time. On these tasks both are the same as A, so they say nothing about test gates or
  extra attempts. They do show the noise: t39 scored 3/5, 1/5 and 4/5 across three effectively identical setups.
- **The reviewer did not rescue a run.** B's reviewer approved 27 runs and 19 of those failed the hidden tests.
  It asked for changes in 7, and all 7 still failed after the fix round. One B run ended with no verdict.
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

t42 to t45 fail for the intended reason, a decision the agent did not ask about. They are the cleanest tasks so
far. Across the study, rules shown only by code keep producing debatable tests (t22, t23, t46, t48).

## Limits

- 7 tasks at 5 runs per cell. The earlier simulation wanted about 20 tasks to detect a 20-point gap.
- Sonnet 5.5 only. The Haiku and Opus part of the study has not run.
- The second score and the list of debatable tests are one reviewer's judgement, made after the results.
- Task writers were Sonnet agents, and the debatable tests are partly a flaw in those tasks.
- Sign tests are unadjusted for comparing several setups, which only makes them more generous.
- Repeated runs in `A` use the same prompt and repo, so they are not independent tasks.

## Harness fixes from this review

- The limit detector now recognises "You've hit your 5-hour limit".
- `hidden_tests.txt` now keeps the whole test output. It kept only the last 1,500 characters, though recorded
  pass and fail counts were never affected. `scripts/rescore_main_sweep.py` regraded the kept worktrees, without
  any model calls, and every count matched the record.

Reproduce: `python scripts/rescore_main_sweep.py <sweeps folder> results/20261101T145*.jsonl`
