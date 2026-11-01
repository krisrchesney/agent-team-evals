# t28-config-rename: where each hidden-test rule is shown

The repo is a 3,000-line job daemon. `queue_workers` is named in eleven modules, a doc page and two example
configs. The only precedent for a rename (`loglevel` -> `log_level`) is spread over four files. This
file is outside `repo/`, so agents never see it.

| Test group | Rule | Shown by (repo/) |
|---|---|---|
| `TestNewName` | the new name is accepted from a JSON file, an INI file, `JOBD_WORKER_THREADS` and `--worker-threads`; default and range unchanged; the old key is gone from `SETTINGS` and `as_dict()`; errors name the new setting | prompt; `config/schema.py` (`SETTINGS` drives file, env and flag handling); `config/values.py` |
| `TestOldName`: file, INI, environment | the old name keeps working in those sources and warns once with both names | prompt ("the same way the other renamed setting already does"); `config/deprecations.py` module docstring and `RENAMED`; `config/env.py` reads `RENAMED` names; `tests/test_config.py::test_loglevel_is_the_old_name_of_log_level` (warning text) |
| `test_old_flag`, `test_old_flag_stays_out_of_help` | the old flag is still accepted but hidden from `--help` | `config/cli_flags.py` (`--loglevel` with `help=SUPPRESS` and the `read` name list; this is not driven by `RENAMED`) |
| `test_new_name_wins_when_a_source_has_both`, `test_source_priority_...` | the new name wins inside a source; across sources the usual order applies whichever name was used | `deprecations.py` docstring ("if a source gives both names, the new name wins"); `config/loader.py` |
| `test_errors_in_the_old_name_name_the_new_one` | rename is applied before validation | `config/loader.py` (`apply_renames` before `coerce`) |
| `test_old_attribute_still_reads_with_a_warning` | `settings.queue_workers` still answers, with a warning | `config/settings.py` `loglevel` property; `deprecations.py` docstring |
| `TestEverythingUsesTheNewName` | pool, scheduler, autoscaler, backpressure, limits, health, metrics, status, report, capacity, doctor, config show/defaults and the daemon all read `worker_threads` and print it. The `strict` helper turns the old-attribute warning into an error, so a module that still reads `settings.queue_workers` fails | prompt ("everything that shows or uses the setting should use the new name"); `grep queue_workers` |
| `TestCommandLineAndDocs` | CLI status/config output and the stderr warning; docs: new name in the main table, old name only under "Renamed settings"; example configs load without warnings | `docs/settings.md` ("Renamed settings" table), `tests/test_config.py::test_every_setting_is_documented` and `test_example_configs_load_without_warnings` |
| `test_reg_loglevel_still_works_everywhere` | the existing rename is not broken | `tests/test_config.py` |

What makes it hard: no single place to edit. The rename touches `schema`, `deprecations`, `settings`,
`cli_flags`, nine consumers, the docs and the examples. The environment and file paths are automatic once
`RENAMED` has the entry, but the flag and the attribute alias are not, and a straggler that still reads
the old attribute only shows up as a warning at run time. Mistakes the tests catch: forgetting the hidden
flag, forgetting the attribute alias, leaving a module on the old attribute, leaving the docs or examples on
the old name, validating before renaming.
