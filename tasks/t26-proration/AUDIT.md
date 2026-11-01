# t26-proration: where each hidden-test rule is shown

The repo is a 3,000-line billing library. One rule, "prorate on a flat 30-day month (360-day year)",
is written out separately in five modules, each with its own rounding. This file is outside `repo/`,
so agents never see it.

| Test group | Rule | Shown by |
|---|---|---|
| `test_r1_*` (`TestPlanChange`) | plan change credits/charges `remaining days / days in the real period`; same rounding as today (Decimal, half up); yearly plans use 365/366 | prompt (real length of the billing period, 28/29, 365/366, "keeps the rounding it has today"); `plan_change.py` (the `DAYS_PER_MONTH` basis) |
| `test_r2_*` (`TestFirstInvoice`) | the first, partial month is `stub days / days in that cycle`, integer floor division as today; the cycle is the one anchored on `anchor_day` | prompt; `invoicing.py` `bill_signup` (`min(stub_days, 30) // 30`); `periods.month_period` |
| `test_r3_*` (`TestCancellation`) | cancel refunds `unused days / period days`, rounded **down** | prompt; `cancellation.py` (`ROUND_DOWN`, literal 30 / 360) |
| `test_r4_*` (`TestSeats`) | added seats are charged `remaining / period days`, halves rounded up with integer math | prompt; `seats.py` |
| `test_r5_*` (`TestAllowance`) | included units in the first partial period are `units * stub days / period days`, floored | prompt ("everywhere it prorates"); `quotas.py` |
| `test_reg_*` (`TestThirtyThatMustStay`) | other 30s are not proration: revenue recognition already uses the days of its own period, overdue buckets, suspension, trial length, MRR | prompt ("nothing that merely uses the number 30 for something else should change"); `revenue.py`, `dunning.py`, `reports.py`, `trial.py`, `constants.py` |
| other `test_reg_*` | 30-day months, anchor-day starts, yearly first invoices, renewals, removing seats keep today's results | existing code and `tests/test_billing.py` |

Rounding is the trap inside the trap: a rewrite that routes all five through one helper with one
rounding mode fails some of the exact cents (floor in `bill_signup`/`quotas`, down in `cancel`, half up
in `change_plan`/`add_seats`). Each is visible in the code it replaces.

What makes it hard: the rule is not in one place. `grep 30` finds hits in a dozen files; five places are the
rule (with different spellings: `DAYS_PER_MONTH`, `30`, `360`, `30 * (12 if ...)`, `12 * 30`) and the
rest must stay. Missing any one of the five fails its group; changing the unrelated 30s (aging, dunning,
trial) fails the regression group.
