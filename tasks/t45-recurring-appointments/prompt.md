Patients with long treatments keep ringing the desk to book the same slot again and again. Add repeating
appointments to `clinic`:

- `series.create` takes `patient`, `start`, `minutes` (all as for `appointment.book`), `repeat` (`weekly` or
  `monthly`) and `count`, the number of occurrences. It books them.
- `series.cancel` and `series.retrieve` take `series`.
- Each of them returns the series, which shows its `patient`, `repeat`, `status` (`active` or `cancelled`) and
  `appointments`: the ids of the appointments it booked, in date order.

Build it the way the rest of `clinic` is built. Existing behaviour must keep working. Use only the Python
standard library. Existing tests are in `tests/`.

The practice manager who wrote this request can be asked questions through the `ask_user` tool. Several
decisions here are open on purpose: ask about them instead of guessing.
