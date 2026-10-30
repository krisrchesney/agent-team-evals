# t20-vendor-import: where each hidden-test rule is written

The prompt only says "load Corvid like Acme and Bolt" and points at the supplier's notes. Every rule
the hidden tests check is written in the starting repo. This file is outside `repo/`, so agents
never see it.

| Test group | Rule | Where in repo/ |
|---|---|---|
| `test_imp1_*`, `test_imp2_*` | subclass `BaseImporter`; register in `VENDORS` under `corvid` | docs/IMPORTERS.md items 1-2; ingest/importers/registry.py |
| `test_vendor_the_real_export`, `_records_are_invoice_lines` | full mapping of the sample export | docs/vendors/corvid.md; samples/corvid_2024-05.csv; docs/IMPORTERS.md items 7-11 |
| `test_vendor_german_number_format`, `test_imp4_bad_amounts` | decimal comma, `.` thousands, max 2 decimals via `money.to_cents(text, ",", ".")` | docs/vendors/corvid.md `Einzelpreis`; docs/IMPORTERS.md items 4, 8; ingest/money.py docstring |
| `test_vendor_dates`, `test_imp4_bad_dates` | `DD.MM.YYYY` for both dates; `bad_date` | docs/vendors/corvid.md `Datum`, `Faellig`; docs/IMPORTERS.md item 4 |
| `test_imp10_*`, `test_cfg_*` | empty due date = invoice date + `terms_days` (45 for corvid) from settings | docs/IMPORTERS.md item 10; config/vendors.json |
| `test_imp9_currency` | empty currency = settings currency (EUR); unknown currency error | docs/IMPORTERS.md items 4, 9; config/vendors.json; ingest/money.py `CURRENCIES` |
| `test_imp7_*` | `normalize.sku`, `normalize.text` | docs/IMPORTERS.md item 7; docs/vendors/corvid.md `Artikel` |
| `test_imp11_*` | ids stripped, `line_no` int | docs/IMPORTERS.md item 11 |
| `test_vendor_quoted_fields`, `test_imp3_*` | quoting, BOM handled by the base class via `delimiter = ";"` | docs/vendors/corvid.md first paragraph; docs/IMPORTERS.md items 1, 3 |
| `test_imp4_*` (rows) | codes, one error per row, field order, import continues, line numbers | docs/IMPORTERS.md item 4 |
| `test_imp5_*` | `STORNO` skipped silently and checked first | docs/IMPORTERS.md item 5; docs/vendors/corvid.md `Status` |
| `test_imp6_*` | duplicates (base class) | docs/IMPORTERS.md items 3, 6 |
| `test_reg_*` | Acme and Bolt unchanged | repo/tests; samples |

What makes it under-specified: the supplier's notes say what the columns mean, not how `ingest`
treats them. The 45-day terms, the EUR default, skipping cancelled lines silently and before any
validation, normalizing article numbers, the error codes, and the field order for "first problem"
live only in docs/IMPORTERS.md and config/vendors.json.
