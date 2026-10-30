# How operations are built

Every public operation follows this checklist. Reviewers reject changes that skip a step.
`paydesk/ops/charges.py` is the reference implementation; copy its shape.

1. **One function per operation**, registered with `@operation("<object>.<verb>", scope=...)`
   from `paydesk.ops`. The scope comes from `docs/API.md`. `Service.call` looks the operation up
   and checks the scope before the function runs; never check scopes inside the function.
2. **Operation modules are loaded explicitly.** A new module under `paydesk/ops/` must be added to
   `MODULES` in `paydesk/ops/__init__.py`, or its operations are never registered.
3. **Validate every parameter first**, before reading or changing any state, with the helpers in
   `paydesk/validate.py` and `paydesk/money.py`. Errors are `PaydeskError` subclasses with the code
   and `param` given in `docs/ERRORS.md`.
4. **No side effects on failure.** If an operation raises, nothing has changed: no stored object,
   no ledger transaction, no audit entry, no event. Do every check before the first write.
5. **Idempotency.** Every operation that changes state runs its body through
   `svc.idempotency.run(ctx, name, params, body)`, where `params` holds every parameter as the
   caller passed it (after defaults are *not* filled in). Read-only operations do not.
6. **Money moves only through the ledger** (`svc.ledger.post`), using the accounts in
   `docs/LEDGER.md`. Never adjust a balance any other way.
7. **Audit every state change**, after it succeeds: `svc.audit.record(actor=ctx.actor,
   action=<operation name>, object_id=<id of the object created or changed>, at=<now>,
   details=...)`. What goes in `details` is listed per operation in `docs/API.md`.
8. **Emit events after the change**, as listed in `docs/EVENTS.md`, in the order listed there.
9. **Return the serialized object** (`obj.serialize()`), a plain dict. Ids come from
   `svc.new_id(prefix)` and times from `svc.now()`; call `svc.now()` once per operation and use
   that value everywhere (object, audit entry, events).
