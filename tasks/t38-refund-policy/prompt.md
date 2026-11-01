Support is refunding customers by hand. Add partial refunds to `payledger`:

- `refund.create` takes `charge` (the charge id), `amount` in cents and an optional `reason`. It
  returns the refund, which shows its `charge`, `amount`, `tax` (the part of the amount that is tax),
  `reason` and `approved_by`.
- `refund.retrieve` takes `refund`; `refund.list` takes `charge`.
- A charge can be refunded in several pieces. Its `refunded` field is the total handed back so far, and its
  `status` becomes `partially_refunded` or, once everything is back, `refunded`.
- Every refund shows up in the ledger.

Build it the way the rest of `payledger` is built. Existing behaviour must keep working. Use only the
Python standard library. Existing tests are in `tests/`.

The product owner who wrote this request can be asked questions through the `ask_user` tool. Several
product decisions here are open on purpose: ask about them instead of guessing.
