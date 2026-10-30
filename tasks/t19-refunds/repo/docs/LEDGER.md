# Ledger

`svc.ledger` is a double-entry ledger. A transaction is `post(ref, currency, entries)`, where
`entries` is a list of `(account, amount)` pairs that sum to zero and `ref` is the id of the object
that caused it.

Accounts:

- `customer:<account id>`: what the customer has paid (goes negative as they pay).
- `merchant_revenue`: money the merchant has received.

Movements:

| Event | `ref` | Entries |
|---|---|---|
| capture | charge id | `customer:<account>` -amount, `merchant_revenue` +amount |
| refund | refund id | `merchant_revenue` -amount, `customer:<account>` +amount |

Authorizing and voiding move no money.
