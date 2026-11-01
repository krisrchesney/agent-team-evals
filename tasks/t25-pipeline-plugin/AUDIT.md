# t25-pipeline-plugin: where each hidden-test rule is shown

The repo has no docs folder. The prompt names the stage, its options, the output record shape and
"build it the way the other stages are built". Everything else is shown by the base class
(`datapipe/stage.py`, `pipeline.py`) and the five existing stages (`map`, `filter`, `dedupe`, `batch`,
`lookup`). This file is outside `repo/`, so agents never see it.

| Test | Rule | Shown by (repo/) |
|---|---|---|
| `test_registered_and_named_after_its_type` | `@register("rollup")` and import in `plugins/__init__.py`; name defaults to the type | `plugins/__init__.py` comment; `config.build_stage` |
| `test_count_is_the_default_...`, `test_several_by_fields`, `test_every_aggregate`, `test_aggregates_come_in_the_order_listed`, `test_sums_of_whole_numbers_stay_whole`, `test_empty_input` | output shape and order | prompt |
| `test_zero_and_empty_string_are_real_group_values` | only `None` or an absent field is "missing"; `0` and `""` are values | `Stage.need` |
| `test_count_only_does_not_read_the_field` | `field` is only needed (and only checked) when an aggregate uses it | prompt ("`field` is required unless `count` is the only aggregate") |
| `test_nothing_is_emitted_before_the_input_ends` | results leave in `flush()`, not `process()`; `process` returns `[]` | `batch.py`; `Stage` docstring; `pipeline.run` |
| `test_flushed_results_go_through_the_stages_after_it`, `..._become_dead_letters` | follows from using `flush()` | `pipeline.run` (`_feed(level + 1, ...)`) |
| `test_a_stage_before_it_can_flush_into_it` | integration check of the flush order | `pipeline.run` |
| `test_each_run_starts_empty` | state is reset in `open()` (and not left over from `__init__` or a previous run) | `dedupe.py`, `batch.py` (`open` resets) |
| `test_flushing_empties_the_stage` | `flush()` hands over the state and clears it | `batch.py` `_take` / `flush` |
| `test_inputs_are_not_changed_and_outputs_are_new` | stages copy records, never mutate them or pass them through by reference | `map_.py`, `filter_.py`, `dedupe.py`, `batch.py`, `lookup.py` all `dict(record)` |
| `test_bad_records_are_rejected_with_...` | data problems call `self.reject(record, reason)` (via `need` for missing fields); unhashable keys and non-numbers (a bool is not a number) are rejects too; dead letters come from the base class with the record object | `Stage.need`, `Stage.handle`; `dedupe.py` (unhashable key); `filter_.py` (`_is_number`) |
| `test_a_rejected_record_does_not_create_a_group` | validate everything before changing state | `dedupe.py` (hash check before `seen.add`) |
| `test_on_reject_fail_stops_the_run` | free from the base class once `reject` is used rather than raising | `Stage.handle` |
| `test_bad_config_is_a_config_error_...` | options are validated in `configure()` with `ConfigError(self.name, message)`, at build time; unknown options, `on_reject` and missing required options come from `Stage.__init__` (so `OPTIONS` and `REQUIRED` must be set); non-empty lists of non-empty strings; no bools or wrong types | `stage.py`; `dedupe.py`, `batch.py`, `filter_.py` `configure` |
| `test_the_error_names_the_stage_by_its_name` | the stage's own name (not its type) goes into the error | `Stage.__init__`; `config.build_stage` |
| `test_valid_options_are_accepted`, `test_stage_names_must_be_unique` | `Pipeline` checks names; options are not over-validated | `pipeline.py` |
| `test_cli`, `test_other_stages_unchanged` | works through the CLI; regression | `cli.py`; `tests/test_pipeline.py` |

What makes it hard: a stage that aggregates must hold state, which is a different shape from the other
four per-record stages except `batch`. The obvious implementation emits from `close()` or from
`process`, keeps its state across runs, rejects nothing (or raises `ValueError`, which aborts the run
as a `StageError`), forgets `OPTIONS` / `REQUIRED` (so the base class refuses its options), builds the
group on a record that is rejected later, or treats `0` as missing. Each of these is visible in the
base class or in a neighbouring stage.
