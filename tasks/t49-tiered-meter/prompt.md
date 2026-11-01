Heavy users of `meterd` want volume pricing. Add a `tiered` meter:

- Usage is recorded on it like on the other meters (`usage.record` with `meter` set to `tiered`).
- It prices a billing period's usage in tiers: the first 100 units cost 7.5 cents each, units 101 to
  1,000 cost 6.2 cents each, and every unit after that costs 4.5 cents.
- It puts one line on the invoice, after the lines of all the other meters. The line's `quantity` is
  the units used; its `amount` is the price in cents.

Build it the way the other meters are built, so it fits with everything else in the service. Existing
behaviour must keep working. Use only the Python standard library. Existing tests are in `tests/`.
