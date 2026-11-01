# t24-cli-export: where each hidden-test rule is shown

The repo has no docs folder and no README: the prompt names the command, `--output`, `--format`, the
summary keys and "the same filters as `list`". Everything else is shown by the existing subcommands
(`add`, `list`, `show`, `done`, `stats`, `backup`) and the helpers they share. This file is outside
`repo/`, so agents never see it.

| Test | Rule | Shown by (repo/) |
|---|---|---|
| all of them (registration) | a command module is added to `COMMANDS` and defines `NAME`, `HELP`, `configure`, `run` | `commands/__init__.py` comment; every command module |
| `test_csv_is_the_default_...` | header is `model.FIELDS`; rows are `Task.to_row()` (tags joined with `;`, empty due) | `model.py` (`FIELDS`, `to_row` docstring); `--plain` in `list_.py` |
| `test_csv_survives_...` | cells go through the csv module; files are UTF-8 | `atomicio.write_text` (`encoding="utf-8"`, `newline=""`); store and backup write UTF-8 |
| `test_json_file_is_the_list_json_items`, `..._utf8_...` | the JSON file is a list of `Task.to_dict()`, as `list --json` shows each item | prompt; `model.to_dict` docstring; `list_.py` |
| `test_tasks_are_in_id_order` | tasks come from `filters.select`, which sorts by id | `filters.py` |
| `test_filters_work_like_list`, `test_json_filters_and_count` | use `add_filter_args` and `select` | prompt ("same filters as `list`"); `list_.py`, `stats.py` |
| `test_unknown_project_is_not_found` | an unknown project is `NotFound`, exit 3, `tasklog: error: ...`, nothing written | `filters.select`; `exitcodes.py`; `console.py` |
| `test_bad_date_is_a_usage_error`, `test_bad_format_and_missing_output...` | bad arguments are usage errors, exit 2, raised before anything is written (`select` runs first; argparse errors go through `Parser.error`) | `dates.py`, `cli.py`, `filters.py` |
| `test_text_summary` | one text line with the count and the path, via `con.say` | `backup.py` (`backed up N tasks to PATH`), `add.py` |
| `test_json_summary`, `..._as_given` | `{"command": NAME, "count": n, "format": ..., "output": path as given}`; nothing else on stdout; `command` is the subcommand name | prompt (keys); `backup.py` (`command`, `count`, `output`), every `con.emit` |
| `test_quiet_silences_the_text_but_not_json` | `con.say` honours `-q` and is silent in `--json`; `con.emit` prints in JSON mode whatever `-q` says | `console.py` |
| `test_the_store_is_not_changed`, `test_a_missing_store_is_empty...` | read-only commands never call `store.save()`; a missing store is empty | `list_.py`, `stats.py`, `store.py` |
| `TestEmpty` | an empty result is not an error: still exit 0, still writes the file, one `con.warn(...)` line on stderr; warnings ignore `-q` | `list_.py`, `stats.py`, `backup.py` (all warn when empty); `console.warn` |
| `test_existing_output_is_a_conflict`, `test_force_replaces_the_file` | an existing output file is `Conflict` (exit 5) unless `--force`; the file is left untouched | `backup.py` |
| `test_unwritable_output_is_an_io_failure` | `OSError` from the write becomes `IoFailure`, exit 4, message names the path | `backup.py`, `store.save` |
| `test_no_temporary_files_are_left_behind` | write through `atomicio.write_text` | `atomicio.py`; `backup.py` |
| `test_errors_in_json_mode` | raising the typed `CliError` lets `Console.error` print the JSON error body with `command` and `code` | `errors.py`, `console.py`, `cli.main` |
| `test_a_corrupt_store_is_an_io_failure` | free once the command is registered | `store.py` |
| `TestRegression` | regression | `tests/test_cli.py` |

What makes it hard: the prompt says "build it like the other subcommands" and nothing more. A simple
export that opens the file, writes it, prints a line and returns exits with the wrong code on a missing
project, an existing file and an unwritable path, overwrites files silently, leaves no warning for an
empty result, prints the wrong JSON envelope, and may crash with a traceback or mangle non-ASCII text.
`--force` is not in the prompt; it is the flag `backup` already has for the same situation.
