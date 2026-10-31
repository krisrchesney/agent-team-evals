People keep asking for their task list in a spreadsheet, and for a file other tools can read. Add an
`export` subcommand to `tasklog`:

    tasklog export --output PATH [--format csv|json] [--json] [filters]

- It writes the tasks that match the same filters as `list` to `PATH`. `--format` is `csv` (the default)
  or `json`. The CSV has a header row and one row per task. The JSON file is a list of tasks, each one
  shown the way `list --json` shows it.
- With `--json` it also prints a summary of what it did, with `count` (how many tasks were written),
  `format` and `output`.
- It does not change the store.

Build it the way the other subcommands are built, so it behaves like them in the terminal and in
scripts. Existing behaviour must keep working. Use only the Python standard library. Existing tests are
in `tests/`.
