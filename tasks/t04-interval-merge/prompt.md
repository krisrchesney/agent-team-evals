`calkit.intervals` turns a person's busy calendar entries into merged busy blocks and free slots.
Users report that some calendars come out wrong. Fix the module so that it meets this spec:

1. An interval is a two-item list `[start, end]` of numbers with `start < end`, meaning the
   half-open range `start <= t < end`.
2. `merge(intervals)` returns a new list of intervals, sorted by start, with no two of them
   overlapping, that covers exactly the same points as the input. The input may be in any order.
3. Intervals that overlap, or where one starts exactly where another ends, end up in the same
   output interval. Intervals separated by a gap stay separate.
4. `merge()` never modifies its argument: after the call, the input list and every `[start, end]`
   pair in it are unchanged.
5. `free_slots(busy, window_start, window_end)` returns, sorted, every maximal gap inside
   `[window_start, window_end)` that no busy interval covers. Busy intervals that stick out of the
   window are clipped to it; busy intervals entirely outside it are ignored. No gap has zero length.
6. `merge([])` returns `[]`. `free_slots([], a, b)` returns the whole window, `[[a, b]]`.

Keep the public signatures as they are. Use only the Python standard library.
Existing tests are in `tests/`.
