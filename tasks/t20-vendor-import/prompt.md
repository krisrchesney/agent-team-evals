We signed a new supplier, Corvid. Finance wants their invoice exports loaded by `ingest` the same
way Acme and Bolt files are, so `ingest.run_import("corvid", text)` works. Corvid sent notes on
their export format; they are in `docs/vendors/corvid.md`, and there is a real export in `samples/`.

Existing behaviour must keep working. Use only the Python standard library. Existing tests are in
`tests/`.
