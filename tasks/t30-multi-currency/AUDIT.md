# t30-multi-currency: where each hidden-test rule is shown

Category `cross-module`: the prompt lists fourteen numbered requirements, one or more per module, and
the hidden tests (named `test_r<N>_...`) hit every module. No rule depends on anything outside the
prompt and `repo/`. This file is outside `repo/`, so agents never see it.

| Test(s) | Rule | Shown by |
|---|---|---|
| `test_r1_exponents`, `_parse`, `_too_many_decimals`, `_unknown_currency`, `_format`, `_decimal_string` | exponents, minor units, plain int = whole units, format strings, `UnknownCurrency` | prompt 1; `money.py` (the USD versions of every function) |
| `test_reg_percent_and_split` | percent/split unchanged | `money.py` |
| `test_r2_account_currency` | account currency, default USD | prompt 2; `accounts.py` |
| `test_r3_*` (7 tests) | currency from the account; balance per currency; line currency mismatch; void keeps currency | prompt 3; `journal.py` |
| `test_r4_*` (7 tests) | rate lookup by date, inverse, direct wins, identity, `NoRate`, minor-unit conversion across exponents (USD to JPY, USD to KWD), half-away rounding, `InvalidRate` | prompt 4 (all rules written out); rounding rule is also in the `money.py` docstring |
| `test_r5_*` | trial balance per currency, `total_debit` stays USD only | prompt 5; `reports.trial_balance` |
| `test_r6_*` (6 tests) | reporting currency; convert per account; rate on `as_of` / on `end`; current earnings converted; `balanced` judged natively; statement display in account currency | prompt 6; `reports.py` |
| `test_r14_*` | summary converts per account at `as_of`; zero balances skipped | prompt 14 |
| `test_r7_*` (4 tests) | budget currency defaults to the account's; limit parsed in it; per posting date conversion; alerts per budget | prompt 7; `budgets.py` |
| `test_r8_*` (6 tests) | invoice currency from receivable; JPY prices and tax; other accounts must match, nothing recorded; payments; aging per invoice, in a chosen currency | prompt 8; `invoices.py` |
| `test_r9_*` | recurring template checked per currency at `add` (its own copy of the zero-sum check) | prompt 9; `recurring.py` |
| `test_r10_*`, `test_reg_interest_in_usd` | interest in the account's currency, display, income account mismatch | prompt 10; `interest.py` |
| `test_r11_*`, `test_reg_usd_reconcile` | statement amounts and tolerance in the account's currency, display | prompt 11; `reconcile.py` |
| `test_r12_*` | CSV currency column, decimals per currency, import with and without the column, mismatch, row number in the error | prompt 12; `csvio.py` (hard-coded `// 100` in `_fmt`) |
| `test_r13_*` | dump/load keep currencies and rates, JSON safe, older dump reads as USD | prompt 13; `snapshot.py` |
| `test_reg_usd_flow` | USD behaviour unchanged | `tests/test_ledger.py` |

Rates used by every test are set in `new_ledger()` (EUR/USD 1.10 from 2026-01-01 and 1.20 from
2026-02-01; USD/JPY 150).

What makes it hard: nothing is subtle, but the change is wide. Fourteen modules each need their own
edit, several do their own arithmetic (`csvio._fmt` hard-codes `// 100`, `recurring.add` re-implements
the zero-sum check, `money.parse_amount` treats a plain int as dollars, `interest` formats its own
display), and a few rules combine two modules (invoices post through the journal, so a currency
mismatch there must leave nothing recorded). An agent that threads `currency` through the obvious
modules and misses `recurring`, `csvio`, `reconcile` or `snapshot` fails a handful of tests.
