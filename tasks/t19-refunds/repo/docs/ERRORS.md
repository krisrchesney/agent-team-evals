# Errors

Every error is a `paydesk.errors.PaydeskError` subclass with a stable `code` and, when one
parameter is to blame, `param` set to that parameter's name.

| Class | Code | `param` | When |
|---|---|---|---|
| `InvalidRequest` | `invalid_param` | the parameter | an id parameter is missing, empty or not a string |
| `InvalidRequest` | `invalid_amount` | `amount` | amount is not an int, is a bool, or is not positive |
| `InvalidRequest` | `invalid_currency` | `currency` | currency is not in `paydesk/currencies.py` |
| `InvalidRequest` | `invalid_reason` | `reason` | a refund reason that is not in the list in `docs/API.md` |
| `InvalidRequest` | `amount_too_large` | `amount` | more than the operation allows (capture: more than authorized; refund: more than still refundable) |
| `InvalidRequest` | `charge_not_authorized` | `charge_id` | capture or void of a charge that is not `authorized` |
| `InvalidRequest` | `charge_not_captured` | `charge_id` | refund of a charge that was never captured (`authorized` or `voided`) |
| `InvalidRequest` | `charge_already_refunded` | `charge_id` | refund of a charge whose status is `refunded` |
| `NotFound` | `not_found` | the id parameter | no object with that id |
| `NotFound` | `unknown_operation` | none | `svc.call` with a name nobody registered |
| `Forbidden` | `forbidden` | none | `ctx.scopes` lacks the operation's scope |
| `Conflict` | `idempotency_mismatch` | none | an idempotency key reused with a different operation or different parameters |

Check in this order: parameters (in the order the operation lists them), then the object's
existence, then its state, then amounts against the object.
