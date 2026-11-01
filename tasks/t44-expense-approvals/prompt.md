Expense claims pile up in the finance inbox with nobody sure who has seen them. Add approvals to `spendflow`:

- `expense.submit` takes `expense`: the employee sends a draft in for approval.
- `expense.approve` and `expense.reject` take `expense` and `by`, the employee who is deciding on it.
- Each of them returns the expense. Its `status` is `draft`, `submitted`, `approved` or `rejected`.

Build it the way the rest of `spendflow` is built. Existing behaviour must keep working. Use only the
Python standard library. Existing tests are in `tests/`.

The finance lead who wrote this request can be asked questions through the `ask_user` tool. Several
decisions here are open on purpose: ask about them instead of guessing.
