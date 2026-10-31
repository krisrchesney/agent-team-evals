We want to run small SQL `SELECT` queries over folders of CSV files. `minisql/` has the pieces that already
exist: the CSV catalog, the syntax tree classes and the errors. `parser.py` and `engine.py` are stubs, and
`query()` in `__init__.py` already calls them. `docs/SPEC.md` describes the supported SQL and the exact
semantics (NULLs, joins, grouping, ordering, error cases).
Implement `parse` and `execute` as the spec says. Use only the Python standard library. Existing tests are
in `tests/`.
