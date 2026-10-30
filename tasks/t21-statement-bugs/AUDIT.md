# t21-statement-bugs: where each hidden-test rule is written

The prompt gives two customer complaints (symptoms only). Every rule the hidden tests check is
written in the starting repo or follows from a complaint. This file is outside `repo/`, so agents
never see it.

Planted causes (each one is caught on its own by the hidden tests; checked by reverting one fix at a
time):

1. `stmt/periods.py` `month_period` ignores `utc_offset_minutes` (Keiko's coffee on April's statement).
2. `stmt/periods.py` ends the period at 00:00 on the last day instead of the 1st of the next month
   (Keiko's missing May 31).
3. `stmt/statement.py` and `stmt/balances.py` use `store.all()` (every version) instead of the latest
   version of each transaction (Dan's double payment and wrong closing balance). Fixing only the
   lines leaves opening balances wrong.
4. `stmt/render.py` prints UTC dates instead of local dates.

| Test group | Rule | Where |
|---|---|---|
| `test_report_*` | the two complaints | prompt |
| `test_s1_*` | local calendar month, end exclusive, any offset incl. negative and half-hour | docs/STATEMENTS.md rule 1; `Account.utc_offset_minutes` in stmt/models.py |
| `test_s2_*`, `test_feed_*` | latest version only, everywhere (lines, both balances, export), status and time from the latest version | docs/STATEMENTS.md rule 2; docs/FEED.md; `TxnStore.current` docstring |
| `test_s3_*` | opening = everything before; closing = opening + lines; continuity | docs/STATEMENTS.md rule 3 |
| `test_s4_*` | order by time, then external_id | docs/STATEMENTS.md rule 4 (already correct) |
| `test_s5_*` | local dates on the statement | docs/STATEMENTS.md rule 5; `periods.local_date` helper |
| `test_reg_*` | render layout and store history unchanged | repo/tests; stmt/render.py; docs/FEED.md |

What makes it under-specified: the prompt names two customers' symptoms. The general rules (any
offset, both balances, export, status changes, posting time moving across months, local dates) are
only in docs/STATEMENTS.md and docs/FEED.md, and the prompt asks for a fix that holds "for every
customer".
