# t41-late-fees: where each hidden-test rule comes from

Category `clarify-first`. The prompt asks for late fees on invoices and leaves five policy decisions open.
They are answered only by `answers.json` (outside `repo/`, served by the `ask_user` tool). Everything else
is shown by the prompt or the repo. Agents never see this file.

| Test (class) | Rule | Source |
|---|---|---|
| `test_operations_are_registered` | `fee.assess`, `fee.list` registered by name; module imported in `ops/__init__.py` | prompt (names); `ops/__init__.py` comment; `ops/registry.py` |
| `test_fee_view`, `test_fee_ids_are_sequential_across_invoices` | id from `svc.ids.new("fee")`, created_at = updated_at = now, version 1, fields `invoice`, `amount`, `period`; invoices assessed in creation order | prompt; `ids.py`, `views.stamp`, `invoice.list` ordering |
| `test_invoice_view_has_late_fees`, `test_invoice_bumped_by_a_fee` | `late_fees` and `balance` (fees included) in the view; every change goes through `store.bump` | prompt; `views.balance` docstring; `invoice.pay` |
| `test_assess_event`, catch-up events | event `fee.assessed`, data `{"fee": view, "invoice": view}`, one per fee | `invoice.paid` data `{"invoice", "payment"}` in `ops/payments.py` |
| `test_assess_twice_charges_once`, `test_nothing_to_assess` | idempotent per day, no event when nothing is due | prompt |
| `test_assess_one_invoice`, `_unknown_invoice`, fee list tests | optional `invoice` read with `require_str`, NotFound param `invoice`, `validate.limit`, `has_more` | prompt; `payment.list` |
| `TestGrace` (5) | first fee on D+6, nothing up to D+5, per invoice, paid invoices excluded | answers.json `grace`; `invoice.pay` sets status `paid` |
| `TestAmount` (8) | 2% of the unpaid invoice amount, floor, minimum 250 | answers.json `amount` |
| `TestRecurrence` (8) | period every 30 days (D+36, D+66), no compounding, missed periods caught up, each on the current unpaid amount, stops when paid | answers.json `recurrence` |
| `TestAllocation` (9) | payments cover unpaid fees first, no reallocation of earlier payments, `paid`/`balance` unaffected by the split, overpay check includes fees | answers.json `allocation`; the overpay rule is `invoice.pay` using `views.balance` |
| `TestCap` (7) | total fees at most 25% of the invoice amount (floor), last fee cut to fit, nothing afterwards, per invoice, paid fees still count | answers.json `cap` |
| `TestRegression` | existing behaviour stays | `tests/test_invoices.py` |

## Decisions, plausible guesses, chance a pure guess passes

| Decision | Answer | Plausible guesses | Tests that fail on a wrong guess | P(guess right) |
|---|---|---|---|---|
| grace | 5 days, first fee D+6 | no grace; fee the day after the due date; 7, 10 or 14 days; 30 days | 5 | about 10% |
| amount | 2%, floor, minimum 250 | 1% or 1.5% or 5%; a flat fee; half-up rounding; no minimum | 8 | about 5% |
| recurrence | every 30 days, no compounding, catch up | a single fee per invoice; monthly on the 1st; compounding; no catch-up | 8 | one fee per invoice about 40%, the full recurrence rule about 10% |
| allocation | fees first | invoice first (the usual accounting default for a simple model); proportional | 4 | fees first about 35% |
| cap | 25%, cut to fit | no cap; 10% or 50% or 100% of the invoice; a fee-count cap | 7 | no cap about 55%; 25% about 8% |

A guess passes only if every decision is right: well under 0.1%. A guesser that only picks sensible
defaults for the plain parts (views, ids, events, idempotence) still passes about 13 of 48.

What makes it hard: the prompt reads like a complete spec, but a fee policy has five independent knobs,
and the interactions between them (catch-up with partial payments, fees-first allocation, cap with a
trimmed last fee) are only exact once each one is known.

## Keyword self-check

Matching returns every entry with at least one keyword hit, so each keyword must point at its own
decision. Generated with `ate.askuser.server._hits` over `answers.json`: for each phrasing, the ids
that match (want exactly the decision asked about).

| Question | Decision asked | ids matched |
|---|---|---|
| Is there a grace period before fees start? | grace | grace |
| How many days after the due date does the first fee kick in? | grace | grace |
| When do fees start being charged? | grace | grace |
| What is the fee rate, and how do I round it? | amount | amount |
| Is the fee a percentage or a flat fee? | amount | amount |
| Is there a minimum fee? | amount | amount |
| Is the fee charged once or every month? | recurrence | recurrence |
| Should fees compound on earlier fees? | recurrence | recurrence |
| If assessment is skipped for a few weeks, do I catch up on the missed periods? | recurrence | recurrence |
| When a customer makes a partial payment, does it go to fees or the invoice first? | allocation | allocation |
| How should payments be applied to an invoice that has fees? | allocation | allocation |
| Is there a maximum total of late fees per invoice? | cap | cap |
| Should fees stop at some ceiling? | cap | cap |
| Is there a cap on the total fees? | cap | cap |
| What should the fee id look like? | (none: not a decision) | none |
| Which event should fee.assess emit? | (none: not a decision) | none |
| Does fee.assess return a list of fees? | (none: not a decision) | none |
| Is the due date inclusive for payments? | (none: not a decision) | none |
