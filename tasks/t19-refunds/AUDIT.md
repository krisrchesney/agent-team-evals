# t19-refunds: where each hidden-test rule is written

The prompt is deliberately short. Every rule the hidden tests check is written in the starting repo
(which the agent sees); none is only in the hidden tests. This file is outside `repo/`, so agents
never see it.

| Test group | Rule | Where in repo/ |
|---|---|---|
| `test_api_operations_are_registered` | operation names; modules must be listed in `MODULES` | docs/API.md Refunds table; docs/CONVENTIONS.md item 2; paydesk/ops/__init__.py |
| `test_api_full_refund_by_default`, `_partial_then_rest`, `_several_partials`, `_default_amount_is_what_was_captured` | default amount = captured minus refunded; statuses `partially_refunded` / `refunded`; `refunds` list oldest first | docs/API.md Charges (statuses, `refunds`) and Refunds bullets |
| `test_api_refund_object_shape`, `_currency_is_the_charges` | refund object fields; currency from charge; `status` `succeeded`; ids from `svc.new_id("re")` | docs/API.md refund object; docs/CONVENTIONS.md item 9 |
| `test_api_reasons` | the three reasons, default `requested_by_customer` | docs/API.md Refunds bullets |
| `test_api_retrieve`, `test_api_scopes` | `refund.retrieve`; scopes `refunds:write` / `refunds:read` | docs/API.md Refunds table |
| `test_errors_*` | classes, codes, `param`, check order | docs/ERRORS.md table and last paragraph; paydesk/validate.py, paydesk/money.py |
| `test_conv4_*` | no side effects on failure (incl. Forbidden) | docs/CONVENTIONS.md item 4 |
| `test_conv5_*` | idempotency via `svc.idempotency.run`, params as passed, failures not stored, reads not keyed | docs/CONVENTIONS.md item 5; paydesk/idempotency.py docstring |
| `test_ledger_*` | refund ledger entries, `ref` = refund id | docs/LEDGER.md Movements table |
| `test_conv7_*` | audit entry and its `details` | docs/CONVENTIONS.md item 7; docs/API.md "Audit details" for refunds |
| `test_events_*` | `refund.created` then `charge.refunded`, data shapes, none for reads | docs/EVENTS.md table |
| `test_conv9_*` | one `svc.now()` per operation; ids from `svc.new_id` | docs/CONVENTIONS.md item 9 |
| `test_reg_*` | existing behaviour | repo/tests, paydesk/ops/charges.py |

What makes it under-specified: the prompt names only `docs/API.md`. Ledger entries, the audit
entry, both events and their order, idempotency, the module registration in `MODULES`, error codes and
check order, and the single clock reading are written only in the other docs or shown by
`paydesk/ops/charges.py`.
