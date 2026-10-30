`logpipe` parses a log file (`parse.py`), keeps the records that pass the filters (`filters.py`),
rewrites them with transforms (`transforms.py`) and prints them in a format (`formats.py`);
`pipeline.run_pipeline` ties these together and `cli.py` is the command line
(`python -m logpipe FILE [--filter SPEC]... [--transform SPEC]... [--format NAME]`). A spec is
`name:arg`. Extend it so that:

1. Records can carry structured fields. `Record` gets a field `fields`, a dict that defaults to
   empty. In a log line, after the level, the first occurrence of ` | ` (space, pipe, space)
   splits the line: the left part, stripped, is the message (as before) and the right part holds
   the fields, e.g. `100 INFO user logged in | user=bob id=7 note="two words"`. Fields are separated
   by whitespace. A field is `key=value`: the key matches `[A-Za-z_][A-Za-z0-9_]*`; the value is
   either in double quotes (it may contain spaces and may be empty; the quotes are not part of the
   value) or a non-empty run of non-space characters that does not start with a quote (it may contain
   `=`). Fields keep the order they were written in; if a key repeats, the later value wins.
   Anything else in the fields part raises `ParseError("line <n>: bad fields '<fields part,
   stripped>'")`. A line without ` | ` parses exactly as before.
2. New filters: `field:KEY=VALUE` keeps records whose field `KEY` equals `VALUE` exactly (the
   argument is split at the first `=`; a record without that field does not match);
   `since:TS` keeps records with `ts >= TS`; `until:TS` keeps records with `ts < TS`. A
   `field` argument without `=` raises `ConfigError("bad field filter '<arg>'")` and a
   non-integer timestamp raises `ConfigError("bad timestamp '<arg>'")`.
3. New filter `not:<spec>` keeps the records that the filter `<spec>` would drop, for any
   filter spec, including another `not:`. For example `not:level:warn` and
   `not:field:user=bob`. An unknown inner filter raises the same `ConfigError` as it does
   without `not:`.
4. New transform `dedupe:SECONDS` drops a record when an earlier record that this transform
   kept has the same `level` and the same `msg` (fields are ignored) and
   `record.ts - kept.ts < SECONDS`. Only kept records count, and the comparison is against the most
   recent kept one with that level and message. A `SECONDS` that is not an integer of at least 1
   raises `ConfigError("bad dedupe window '<arg>'")`. The message it compares is the message as the
   transforms before it left it (`upper` then `dedupe:5` ignores case, `dedupe:5` then
   `upper` does not).
5. New transform `rename:OLD=NEW` renames the field `OLD` to `NEW` when the record has it, keeping
   the field in its position. If a different field named `NEW` already exists it is removed. A record
   without `OLD` is unchanged. An argument that is not `OLD=NEW` with both parts non-empty raises
   `ConfigError("bad rename '<arg>'")`.
6. Formats show the fields. `text` appends ` | ` and the fields as `key=value`, separated by
   single spaces, in field order, but only when there are fields; a value that is empty or
   contains whitespace is written in double quotes (`note="two words"`). `json` adds a `"fields"`
   object (always present, `{}` when empty) and keeps `"ts"`, `"level"` and `"msg"` as they are.
7. `run_pipeline(lines, filters=(), transforms=(), fmt="text", lenient=False, stats=None)`.
   Order stays: parse, then all filters, then the transforms in the order given, then the
   format. A transform may drop a record; the later transforms and the format then never see it.
   If `stats` is a dict, `run_pipeline` replaces its contents on success with the integer counts
   `read` (records parsed), `skipped` (see 8), `filtered` (records dropped by a filter),
   `deduped` (records dropped by a transform) and `emitted` (lines returned), so that
   `read == filtered + deduped + emitted`. Blank lines are not counted.
8. With `lenient=True` a malformed line (any `ParseError`) is skipped instead of raised and
   counted in `skipped`; the other lines are processed in order. With `lenient=False` the first
   malformed line raises, as today.
9. Transform state belongs to one run. Calling `run_pipeline` twice with the same arguments gives
   the same output both times, and two `dedupe` transforms in one run (say `dedupe:5` and
   `dedupe:60`) each keep their own memory.
10. The CLI gets `--lenient` (passed as `lenient`) and `--stats`, which prints
    `read=<n> skipped=<n> filtered=<n> deduped=<n> emitted=<n>` as one line to stderr after the output
    lines have been printed, on success only. Errors still print `logpipe: error: <message>` to
    stderr, return 2 and print nothing to stdout.
11. Everything else keeps working as it does today: plain lines, `level:`, `contains:`, `upper`,
    `truncate:N`, `redact:WORD`, the `text` output of records without fields, error
    messages for bad lines, levels, unknown names and formats, and `upper`, `truncate` and `redact`
    leaving the fields untouched.

Standard library only. Existing tests are in `tests/`.
