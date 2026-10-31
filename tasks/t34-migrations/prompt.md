We need a schema migration runner for our SQLite databases. `migrator/runner.py` has the `Migrator`
class with its methods stubbed out, and `docs/SPEC.md` describes how every method must behave.
Implement `Migrator` as the spec says. `errors.py`, `clock.py` and `sql.py` are finished; use them.
Use only the Python standard library. Existing tests are in `tests/`.
