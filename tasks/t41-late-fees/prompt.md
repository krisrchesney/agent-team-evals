Customers pay late and we never charge for it. Add late fees to `billbook`:

- `fee.assess` is run once a day. It charges the fees that are due on overdue invoices as of today and
  returns `{"data": [...]}`: the fees it created, each showing its `invoice`, `amount` and `period` (1 for
  the first fee on an invoice, 2 for the next, and so on). It takes an optional `invoice` to assess just
  that one. Running it twice on the same day must not charge twice.
- `fee.list` takes `invoice` and lists the fees charged on it.
- The invoice view gets `late_fees`, the total assessed so far. What the customer owes (`balance`) now
  includes unpaid fees, and an invoice is `paid` only when that balance is zero.

Build it the way the rest of `billbook` is built. Existing behaviour must keep working. Use only the
Python standard library. Existing tests are in `tests/`.

The finance owner who wrote this request can be asked questions through the `ask_user` tool. Several
decisions here are open on purpose: ask about them instead of guessing.
