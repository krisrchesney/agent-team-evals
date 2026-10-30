# paydesk

The core of a small payments service: charges, a double-entry ledger, an audit log and an event
feed. HTTP and storage live elsewhere; this package is the business logic they call.

```python
from paydesk import Context, Service

svc = Service()
ctx = Context(actor="user_42", scopes=frozenset({"charges:write"}))
charge = svc.call("charge.create", ctx, account="acct_1", amount=2500, currency="USD")
svc.call("charge.capture", ctx, charge_id=charge["id"])
```

Read these before adding an operation:

- `docs/CONVENTIONS.md`: how every operation is built (the checklist reviewers use)
- `docs/API.md`: operations, parameters, objects and scopes
- `docs/ERRORS.md`: error classes and codes
- `docs/LEDGER.md`: which ledger accounts each money movement touches
- `docs/EVENTS.md`: the event feed

Run the tests with `python -m unittest discover -s tests -t .`.
