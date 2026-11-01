Staff keep texting each other to trade shifts, and the manager only finds out when somebody doesn't turn
up. Add shift swaps to `rota`:

- `swap.request` takes `shift` and `to_staff`: the person who holds the shift offers it to someone else.
  (Offering a shift to the person who already holds it is an InvalidRequest on `to_staff`.)
- `swap.accept`, `swap.decline`, `swap.cancel` and `swap.retrieve` take the swap's id as `swap`.
  Accepting hands the shift to `to_staff`; declining and cancelling leave it where it is.
- Each of them returns the swap, which shows its `shift`, `from_staff` (the holder who asked), `to_staff`
  and `status`. A swap is `pending`, `accepted`, `declined`, `cancelled` or `expired`.

Build it the way the rest of `rota` is built. Existing behaviour must keep working. Use only the Python
standard library. Existing tests are in `tests/`.

The manager who wrote this request can be asked questions through the `ask_user` tool. Several decisions
here are open on purpose: ask about them instead of guessing.
