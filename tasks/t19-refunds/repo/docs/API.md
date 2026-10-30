# paydesk API

All operations are called as `svc.call(name, ctx, **params)`. The caller's `ctx.scopes` must
include the operation's scope, otherwise `Forbidden`.

## Charges

| Operation | Scope | Parameters |
|---|---|---|
| `charge.create` | `charges:write` | `account` (id), `amount` (int, minor units), `currency` (default `"USD"`) |
| `charge.capture` | `charges:write` | `charge_id`, `amount` (optional, default the full authorized amount) |
| `charge.void` | `charges:write` | `charge_id` |
| `charge.retrieve` | `charges:read` | `charge_id` |

A charge starts `authorized`. Capturing moves it to `captured`; voiding an authorized charge moves
it to `voided`. Refunds move a captured charge to `partially_refunded` and, once everything
captured has been refunded, to `refunded`.

The charge object:

```
{"id": "ch_...", "object": "charge", "account": "acct_1", "amount": 2500, "currency": "USD",
 "status": "captured", "amount_captured": 2500, "amount_refunded": 0, "refunds": [],
 "created": "2024-05-01T12:00:00+00:00"}
```

`refunds` lists the ids of the charge's refunds, oldest first.

Audit details: `charge.create` -> `{"amount": amount, "currency": currency}`;
`charge.capture` -> `{"amount": captured amount}`; `charge.void` -> `{}`.

## Refunds

| Operation | Scope | Parameters |
|---|---|---|
| `refund.create` | `refunds:write` | `charge_id`, `amount` (optional), `reason` (optional) |
| `refund.retrieve` | `refunds:read` | `refund_id` |

A refund returns money from a captured charge. A charge can be refunded several times, as long as
the total refunded never exceeds the amount captured.

- `amount` defaults to everything still refundable on the charge (captured minus already refunded).
- `reason` is one of `duplicate`, `fraudulent`, `requested_by_customer`; default
  `requested_by_customer`.
- Only charges that are `captured` or `partially_refunded` can be refunded.
- Refunds always succeed immediately (`status` is `succeeded`).

The refund object:

```
{"id": "re_...", "object": "refund", "charge": "ch_...", "amount": 1000, "currency": "USD",
 "reason": "requested_by_customer", "status": "succeeded", "created": "2024-05-01T12:00:00+00:00"}
```

`currency` is the charge's currency.

Audit details: `refund.create` -> `{"charge": charge id, "amount": refunded amount}`.
