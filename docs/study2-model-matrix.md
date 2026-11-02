# Study 2: model matrix (interim)

Status: interim working report. The same 11 tasks as the main sweep, 3 runs per task for each setup.

**No model or mixed team passed more tasks than a single Sonnet agent.** Haiku alone did clearly worse. Opus
alone matched Sonnet within noise at about the same token count. A stronger reviewer flagged more runs but
rescued one of 15. Across all seven decision tasks, covering every decision looks necessary but not enough.

## What ran

33 sweeps from `20261101T224154Z` to `20261101T232245Z`, on 2026-11-01: tasks t22, t25, t34, t37, t38, t39,
t40, t42, t43, t44 and t45, by 4 setups, by 3 runs. That is 132 runs and 45,476,907 tokens, against an estimate
of about 50M, in 84 minutes with 11 processes at a time. There were no isolation flags and no errors, and no
run hit the $2 cap (highest about $1.52, API-equivalent estimate, not a charge).

| Setup | What it does |
|---|---|
| A-Opus, A-Haiku | One agent on that model |
| B-hs | Haiku builder and fix round, Sonnet reviewer |
| B-so | Sonnet builder and fix round, Opus reviewer |

The Sonnet baselines are runs 1 to 3 of A and B from the main and clarify sweeps. They ran earlier the same day
and were not rerun. The B baseline leaves out the t37 redo, which replaced a run 5.

## Results

| Task | A-Haiku | A-Sonnet | A-Opus | B-hs | B (Sonnet) | B-so |
|---|---|---|---|---|---|---|
| t22-stock-holds | 1/3 | 0/3 | 0/3 | 1/3 | 0/3 | 0/3 |
| t25-pipeline-plugin | 0/3 | 2/3 | 1/3 | 1/3 | 1/3 | 1/3 |
| t34-migrations | 0/3 | 2/3 | 0/3 | 0/3 | 1/3 | 0/3 |
| t37-mini-sql | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| t38-refund-policy | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| t39-merge-contacts | 0/3 | 1/3 | 0/3 | 0/3 | 1/3 | 0/3 |
| t40-shift-swap | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| t42-book-holds | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| t43-vouchers | 0/3 | 3/3 | 3/3 | 0/3 | 3/3 | 3/3 |
| t44-expense-approvals | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| t45-recurring-appointments | 0/3 | 0/3 | 2/3 | 2/3 | 0/3 | 0/3 |
| **All** | **1/33** | **8/33** | **6/33** | **4/33** | **6/33** | **4/33** |
| Tokens per run | 381,830 | 169,668 | 163,481 | 467,873 | 263,370 | 364,902 |
| Tokens vs A-Sonnet | 2.25x | 1x | 0.96x | 2.76x | 1.55x | 2.15x |

Compared with A-Sonnet on the same task and run number, where only one of the pair passed:

| Setup | Setup only | A-Sonnet only | Sign test p |
|---|---|---|---|
| A-Opus | 2 | 4 | 0.69 |
| A-Haiku | 1 | 8 | 0.04 |
| B-hs | 3 | 7 | 0.34 |
| B-so | 1 | 5 | 0.22 |

These p values are not adjusted for four comparisons. With that adjustment Haiku's gap is about 0.16, so it is
the strongest signal here but not settled.

## What the setups did

- **A stronger reviewer flagged more and rescued little.** The Opus reviewer asked for changes in 15 of 33 runs,
  and 1 of those passed. It approved 18, and 15 of those failed. The Sonnet reviewer over the same tasks and run
  numbers asked for changes in 7 of 33, and none passed.
- **A Sonnet reviewer did not rescue a Haiku builder.** It asked for changes in 2 of 33 runs, and neither passed.
  It approved 31, and 27 of those failed. B-hs still beat A-Haiku, 4 to 1, but at more tokens than any other setup.
- **Opus's two extra passes on t45 are the one place a stronger model looks different.** All 15 Sonnet runs
  on t45 in the clarify sweep failed (A, AS and B, 5 each), but B-hs also passed it twice with a Haiku builder, so this may be how
  questions happened to be worded rather than the model.

## Decisions on the clarify tasks

t42 to t45 each have 5 decisions the agent has to ask about. Over the 48 new matrix runs:

| Setup | Passed | Questions per run | Share of decisions covered | Runs covering all 5 |
|---|---|---|---|---|
| A-Haiku | 0/12 | 1.00 | 65% | 0 |
| A-Opus | 5/12 | 1.50 | 83% | 5 |
| B-hs | 2/12 | 1.00 | 72% | 2 |
| B-so | 3/12 | 2.17 | 82% | 3 |

All 10 runs covering every decision passed, and none of the other 38 did. No run has covered every decision on t42
or t44, so those two remain unknown.

That table leaves out t38, t39 and t40, which also have the ask tool and 4 decisions each. Counting every recorded
run on all seven tasks, across the main, clarify and matrix sweeps:

| Task | Covered every decision: passed | Missed a decision: passed |
|---|---|---|
| t38 | 0/23 | 0/14 |
| t39 | 10/36 | 0/1 |
| t40 | 0/26 | 0/11 |
| t42 | none | 0/27 |
| t43 | 17/17 | 1/10 |
| t44 | none | 0/27 |
| t45 | 4/4 | 0/23 |
| **All** | **31/106** | **1/113** |

So covering every decision looks necessary but not enough. Debatable tests explain part of the t38 and t40 failures
(`test_r1_refund_view` and `test_accept_event` failed in every main-sweep run). Answer sheets match by keyword, so coverage measures what the sheet
recognised, not exactly what the agent understood.

## Near misses

Most failures are close. The mean share of hidden tests passed, with each run counting equally: A-Opus 95.1%,
B-so 95.1%, A-Sonnet 93.8%, B (Sonnet) 93.0%, B-hs 91.6%, A-Haiku 91.1%. I chose this measure after seeing the
results, so it is descriptive only.

## Usage

The 5-hour bar went from 3% to 65% and the weekly bar from 7% to 12%. Other sessions may have added to both.

| Batch | Tokens | 5-hour bar | Weekly bar |
|---|---|---|---|
| A-Opus | 5,394,875 | +27 | +2 |
| A-Haiku | 12,600,421 | +2 | +1 |
| B-hs and B-so | 27,481,611 | +33 | +2 |

Tokens are a poor guide to plan usage across models: Haiku used over twice Opus's tokens and moved the 5-hour bar
by a small fraction as much.

## Limits

- 3 runs per task on 11 tasks. Single-task swings of 1 or 2 passes are within what the main sweep showed for
  identical setups (t39 scored 3/5, 1/5 and 4/5).
- Baselines were not run in the same batch, and rep numbers are not matched runs in any deeper sense.
- These tasks were screened on Sonnet, so they are selected for Sonnet's failure pattern, which may flatter or
  hurt other models. Debatable tests from the main sweep report still count here.
- Every setup runs agents one after another. This says nothing about parallel work.

Reproduce the table: `python -m ate report results/20261101T22*.jsonl results/20261101T23*.jsonl`
