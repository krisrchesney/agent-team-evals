# ingest

Loads supplier invoice exports into one normalized list of invoice lines for finance.

```python
import ingest
result = ingest.run_import("acme", open("samples/acme_2024-05.csv", encoding="utf-8").read())
result.records   # list of InvoiceLine
result.errors    # list of RowError, one per rejected row
```

- `docs/IMPORTERS.md` is the contract every importer meets. Read it before writing one.
- `docs/vendors/` has each supplier's own description of their format.
- `config/vendors.json` holds per-supplier settings (default currency, payment terms).

Run the tests with `python -m unittest discover -s tests -t .`.
