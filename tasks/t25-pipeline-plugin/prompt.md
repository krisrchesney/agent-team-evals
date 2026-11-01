Analysts want per-group totals straight out of a `datapipe` run. Add a `rollup` stage:

- Options: `by`, a non-empty list of field names to group on (required); `field`, the field to
  aggregate; and `aggregates`, a list drawn from `count`, `sum`, `min`, `max` and `avg` with no repeats
  (default `["count"]`). `field` is required unless `count` is the only aggregate.
- It holds records back and emits its results when the input ends: one record per group, groups in the
  order they first appeared. Each result has the `by` fields first, then the aggregates in the order
  listed, named `count` and `<aggregate>_<field>` (for example `sum_amount`).

Build it the way the other stages are built, so it works in a pipeline next to them (loading from
config, stats, dead letters, running more than once). Existing behaviour must keep working. Use only the
Python standard library. Existing tests are in `tests/`.
