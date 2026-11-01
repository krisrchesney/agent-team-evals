Marketing wants a loyalty scheme in `orderflow`. Customers earn points when an order is delivered:

- An order earns 1 point for every full 10.00 of its total (totals are in cents).
- A customer can earn at most 50 points a day. Points beyond that are not credited; if nothing is left
  to credit, credit nothing.
- Each award produces a `points.awarded` event carrying the `order`, the `customer`, the `points`
  credited and the customer's new `balance`.
- `customer.points` takes `customer` and returns `{"customer": ..., "balance": ...}`; a customer who
  has never earned anything has a balance of 0.

The points should be worked out after the limit checks on an order and before notifications go out.
Build it the way the rest of `orderflow` is built, so it fits with everything else in the service.
Existing behaviour must keep working. Use only the Python standard library. Existing tests are in
`tests/`.
