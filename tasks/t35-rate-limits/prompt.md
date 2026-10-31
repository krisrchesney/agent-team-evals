We need a small rate-limiting library for our API gateway. `ratelimit/` has the package skeleton:
the decision type, clocks, errors and an in-memory store are finished, and `rules.py`, `limiter.py` and
`JsonFileStore` in `store.py` are stubs. `docs/SPEC.md` says how each of them must behave.
Implement the stubs as the spec says. Use only the Python standard library. Existing tests are in `tests/`.
