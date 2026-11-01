# t38-refund-policy: where each hidden-test rule comes from

Category `clarify-first`. The prompt asks for partial refunds on a payments ledger and leaves four product
decisions open. They are answered only by `answers.json` (outside `repo/`, served by the `ask_user` tool).
Everything else is shown by the prompt or the repo. Agents never see this file.

| Test (class) | Rule | Source |
|---|---|---|
| `TestRegistration` | operations registered by name; module imported in `ops/__init__.py` | prompt (names); `ops/__init__.py` comment; `ops/registry.py` |
| `test_r1_refund_view`, ids | id from `svc.ids.new("refund")`; created_at = updated_at = now, version 1; strings stripped | `ops/charges.py` (`charge.create`), `views.stamp`, `ids.py` |
| `test_r1_reason_*` | optional `reason` read with `optional_str`, blank is invalid; has a non-empty default | `validate.optional_str`; `charge.create` description |
| `test_r1_event` | one event `refund.created`, data has the view and the ledger entry | `charge.created` data `{"charge", "entry"}` in `ops/charges.py` |
| `test_r1_unknown_charge`, `_checked_before_amount`, `_bad_amounts`, `_missing_charge` | `store.get_charge` first (NotFound, param `charge`), then `validate.require_amount` (param `amount`, whole cents 1..max) | `ops/charges.py`, `ops/ledger.py`, `validate.py` |
| `test_r1_failures_change_nothing` | validate and check before any change; ids taken only after; no event on failure | every op in `ops/` |
| `TestChargeAndLedger` | `refunded` = total back, `status` `partially_refunded` / `refunded` (prompt); bump version and `updated_at`; ledger row kind `refund`, negative amount, ref = reason | prompt; `store.bump`; `models.Entry` docstring ("anything handed back is negative"); `charge.create` entry |
| `TestRetrieveAndList` | retrieve by `refund`, list by `charge` ordered by time then id, `limit`/`has_more`, reads emit nothing | prompt; `charge.list`, `ledger.entries`, `validate.limit` |
| `TestWindow` (5) | 30 days from the charge's created_at, exactly 30 days allowed, a second later refused with Conflict on `charge`; per charge; also for later refunds | answers.json `window` |
| `TestOverRefund` (5) | whole refund refused (not clamped) when above what is still refundable, cumulative; Conflict on `amount`; exact remainder fine | answers.json `over_refund` |
| `TestTax` (8) | tax = charge tax * amount / charge amount, half up, at most the unrefunded tax, the refund that completes the charge takes the rest | answers.json `tax` |
| `TestApproval` (7) | more than 10000 cents needs non-blank `approved_by`, exactly 10000 does not, stored stripped, null if absent, per refund | answers.json `approval` |
| `TestRegression` | existing behaviour stays | `tests/test_charges.py` |

## Decisions, plausible guesses, chance a pure guess passes

A pure guess means skipping `ask_user` and picking the most common choice for each decision.

| Decision | Answer | Plausible guesses | Tests that fail on a wrong guess | P(guess right) |
|---|---|---|---|---|
| window | 30 days, inclusive | no window at all; 30 days exclusive; 60 or 90 days; 14 days | 5 | no window 35%, 30-day inclusive about 15% |
| over_refund | reject, Conflict on `amount` | reject; cap down to the remainder; InvalidRequest instead of Conflict | 3 | reject with a Conflict is likely (about 55%), the param is a coin flip within that |
| tax | proportional, half up, capped, last refund takes the rest | no tax split (0); proportional with floor; round half even; proportional without the last-refund rule | 8 | about 10% (needs half up and the remainder rule together) |
| approval | strictly over 10000 needs `approved_by` | no approval at all; threshold 5000 or 50000; inclusive `>=`; different field name | 7 | about 10% |

A guess passes only if every decision is right: well under 1%. A guesser who builds none of the optional
features (no window, no approval, no tax split) still passes the plain tests (view, ledger, event, status,
validation: about 25 of 47) and fails the rest.

What makes it hard: the request reads like a finished spec. The decisions only appear once the agent
thinks about edge cases (late refunds, refunds that add up past the charge, tax on a partial amount,
big refunds), and then has to turn each answer into exact behaviour: inclusive bounds, rounding, error
class and param, what is stored.
