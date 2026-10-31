Shoppers lose items at checkout because stock sells out while they pay. Add holds to `stockroom`:

- `hold.create` puts a hold on some stock for an order. It takes the same arguments as `stock.ship`.
- `hold.release` gives the held stock back, `hold.capture` turns the hold into a shipment once the
  order is paid, and `hold.retrieve` looks a hold up. These three take the hold's id as `hold`.
- Each of them returns the hold. A hold is `active`, `released`, `captured` or `expired`, and it
  lasts 15 minutes.
- While a hold is active, nobody else can get that stock.

Build it the way the rest of `stockroom` is built, so it fits with everything else in the service.
Existing behaviour must keep working. Use only the Python standard library. Existing tests are in
`tests/`.
