Our docs keep shipping numbered lists that skip or repeat a number. Add a `list-numbering` rule to
`mdlint`:

- An ordered list item is a line that starts, with no indent, with a number, a dot, a space and
  some text, such as `3. Mix the paste`. A list is a run of items. It carries on over blank lines and
  indented lines, and ends at any other line; the next item after that starts a new list.
- Item n of a list must be numbered `start + n - 1`. `start` is an option, a whole number of at least 0,
  default 1. Every item that is numbered differently is reported with the message
  `expected N, found M`.

Build it the way the other rules are built, so it fits in a linter next to them (config, severity,
linting more than one document with the same linter). Existing behaviour must keep working. Use only
the Python standard library. Existing tests are in `tests/`.
