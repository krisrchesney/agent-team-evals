We want a small `patch`-like library, `patchkit`. The data types, the line helpers and the errors are
finished. `diff.py`, `parse.py`, `apply.py` and `tree.py` are stubs. `docs/SPEC.md` says how each function
must behave, including how hunks are found when the file has moved on since the diff was made.
Implement the stubs as the spec says. Use only the Python standard library. Existing tests are in `tests/`.
