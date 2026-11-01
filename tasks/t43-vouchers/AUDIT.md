# t43-vouchers: where each hidden-test rule comes from

Category `clarify-first`. The prompt asks for gift vouchers in a shop and leaves five decisions open. They
are answered only by `answers.json` (outside `repo/`, served by the `ask_user` tool). Everything else is
shown by the prompt or the repo. Agents never see this file.

| Test (class) | Rule | Source |
|---|---|---|
| `test_operations_are_registered` | four operations registered by name; module imported in `ops/__init__.py` | prompt (names); `ops/__init__.py` comment; `ops/registry.py` |
| `test_voucher_view` | id `voucher_0001` from `ids.new("voucher")`; amount = balance at issue, `active`; created_at = updated_at = now, version 1 | prompt (fields, `active`); `ids.py`; `views.stamp`; `ops/customers.py` |
| `test_issue_event` | one event `voucher.issued`, data `{"voucher": view}` equal to the return value | `service.call` docstring |
| `test_bad_amounts` | InvalidRequest on `amount` for 0, negatives, floats, strings, booleans, missing | `validate.cents`, used for `total` in `ops/orders.py` and tested in `tests/test_orders.py` |
| `test_failures_change_nothing` (both classes) | no event and no id taken on failure | `service.call` docstring |
| `test_retrieve`, `test_unknown_voucher_and_order`, `test_missing_arguments` | NotFound with param = argument name; `require_str`; reads emit nothing | `store.get_order`; `ops/orders.py`; docstring |
| `test_orders_show_credited` | order view has `credited`, 0 for a new order | prompt (last bullet) |
| `test_redeem_event` | one event `voucher.redeemed` about the voucher, version 2 | docstring |
| `test_order_changes_are_silent_but_stamped` | the order is bumped (version 2, updated_at = now) and emits nothing | docstring ("bump", "other records ... change silently") |
| `TestAmounts` (5) | redeem takes the smaller of balance and what the order owes; the rest stays on the voucher; `used` at zero; a used voucher is a Conflict on `voucher` | answers.json `remainder` |
| `TestValidity` (7) | 365 days, `expires_at` in the view, expired from that moment inclusive, seen by every operation, cannot be redeemed, partly used ones expire with their balance, used and void never expire, no event | answers.json `validity` |
| `TestOnePerOrder` (4) | a second voucher on an order is a Conflict on `order`; refusal changes nothing; other orders unaffected | answers.json `one_per_order` |
| `TestVoid` (7) | only an untouched active voucher can be voided; status `void`, balance 0, event `voucher.voided`; otherwise a Conflict on `voucher` | answers.json `void` |
| `TestSettle` (5) | full cover makes the order `paid` at once (even by a bigger voucher), silently; `order.pay` then conflicts; partial cover stays open | answers.json `settle`; `order.pay` in `ops/orders.py` |
| `TestRegression` | existing behaviour stays | `tests/test_orders.py` |

## Decisions, plausible guesses, chance a pure guess passes

| Decision | Answer | Plausible guesses | Tests that fail on a wrong guess | P(guess right) |
|---|---|---|---|---|
| validity | 365 days, `expires_at`, inclusive | never expires; 6 or 12 months; 1 year as 12 calendar months (same here); no field | 7 | no expiry 45%; exactly 365 days with `expires_at` about 8% |
| remainder | min(balance, owed); rest stays; used voucher is a Conflict | forfeit the remainder; refuse a voucher bigger than the order; refuse a smaller one | 5 | keep the rest about 60% (the used-voucher conflict param `voucher` likely) |
| one_per_order | one voucher per order, Conflict on `order` | several vouchers allowed; Conflict on `voucher` | 4 | about 35% allow several; about 40% refuse with param `order` |
| void | untouched active vouchers only, balance 0 | void anything and zero the balance; void keeps the balance; refund the used part | 7 | about 15% |
| settle | order `paid` automatically on full cover | stays open until `order.pay` | 3 | about 35% |

A guess passes only if every decision is right: well under 1%.

What makes it hard: vouchers look like a small balance field and a status. The decisions are the money
rules around them (what happens to the remainder, what an order does when it is covered, what a voucher
can still do once used or expired), and each one changes visible state that the tests check.

## Keyword self-check

The server answers with every entry that has at least one keyword hit, so each keyword must point at its
own decision. Generated with `ate.askuser.server.match_answer` over `answers.json`: for each phrasing, the
ids that match (want exactly the decision asked about).

| Question | Decision asked | ids matched |
|---|---|---|
| Do vouchers expire? | validity | validity |
| How long is a voucher valid for? | validity | validity |
| Is there a deadline to use a voucher after it is issued? | validity | validity |
| What happens if the voucher is worth more than the order? | remainder | remainder |
| Is the leftover balance kept on the voucher or forfeited? | remainder | remainder |
| Can a voucher be used partially, in several orders? | remainder | remainder |
| What if the voucher does not cover the whole order? | remainder | remainder |
| Can a customer use two vouchers on the same order? | one_per_order | one_per_order |
| Can vouchers be combined on one order? | one_per_order | one_per_order |
| Is a second voucher allowed once the first is applied? | one_per_order | one_per_order |
| Can a voucher that was already used be voided? | void | void |
| What should void do to the balance? | void | void |
| Can I cancel a voucher after part of it has been spent? | void | void |
| Should the order be marked paid when the voucher covers it all? | settle | settle |
| Does the customer still need to call order.pay if nothing is left to pay? | settle | settle |
| What status does the order get when it is fully covered? | settle | settle |
| What should the voucher id look like? | (none: not a decision) | none |
| Which event is emitted when a voucher is issued? | (none: not a decision) | none |
| Should amount be in cents? | (none: not a decision) | none |
| What does retrieve return? | (none: not a decision) | none |
