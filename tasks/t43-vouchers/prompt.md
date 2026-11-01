Customers keep asking to pay with gift vouchers. Add them to `shopcredit`:

- `voucher.issue` takes `amount` in cents and returns a new voucher worth that much.
- `voucher.redeem` takes `voucher` and `order`: it puts the voucher towards paying for that order.
- `voucher.void` and `voucher.retrieve` take `voucher`.
- Each of them returns the voucher, which shows its `amount`, its `balance` (what is left on it) and its
  `status`: `active`, `used` or `void`.
- An order shows how much vouchers have covered so far as `credited`.

Build it the way the rest of `shopcredit` is built. Existing behaviour must keep working. Use only the
Python standard library. Existing tests are in `tests/`.

The shop owner who wrote this request can be asked questions through the `ask_user` tool. Several
decisions here are open on purpose: ask about them instead of guessing.
