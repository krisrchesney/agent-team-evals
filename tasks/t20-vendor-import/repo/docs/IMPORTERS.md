# The importer contract

Finance reconciles every file, so all importers must behave the same way. `ingest/importers/acme.py`
and `ingest/importers/bolt.py` follow this contract; use them as models.

## Shape

1. An importer is a subclass of `ingest.importers.base.BaseImporter` with `vendor` set to the
   supplier's id and `delimiter` set to the file's field separator. It implements
   `parse_row(row)`, which gets one data row as a dict keyed by the header names and returns an
   `InvoiceLine`, or `None` to skip the row.
2. It is listed in `VENDORS` in `ingest/importers/registry.py` under the supplier's id, which is
   also the key of its settings in `config/vendors.json`.
3. `BaseImporter.parse` does the rest: the UTF-8 byte-order mark, line numbers, duplicate lines and
   collecting errors. Do not reimplement those.

## Rows

4. **Bad rows never stop an import.** A row that cannot be loaded raises `RowProblem(code)` from
   `parse_row`; the base class records a `RowError(line, code)` and carries on. One error per
   rejected row, using the first problem found, checking the fields in the order of the
   `InvoiceLine` fields. Codes:

   | Code | When |
   |---|---|
   | `missing_field` | a required field (invoice id, line number, sku, quantity, unit price, invoice date) is empty after stripping |
   | `bad_qty` | quantity is not a whole number, or is less than 1 |
   | `bad_amount` | unit price is not a valid amount for the supplier's number format, or is negative |
   | `bad_date` | a date does not match the supplier's date format, or is not a real date |
   | `unknown_currency` | a currency that is not in `ingest/money.py` `CURRENCIES` |

   Line numbers are physical lines of the file, header = line 1 (the base class tracks them).
5. **Cancelled lines are skipped, not rejected.** If the supplier marks a line as cancelled or void,
   `parse_row` returns `None`: no record and no error. Check this before validating anything else
   in the row.
6. Duplicate `(invoice_id, line_no)` pairs inside one file: the first is kept and later ones get
   `duplicate_line` (base class).

## Fields

7. `sku` goes through `normalize.sku` and `description` through `normalize.text`. Never store a
   supplier's raw spelling: finance matches on the normalized forms.
8. Money is integer cents. Convert prices with `money.to_cents(text, decimal_sep, thousands_sep)`
   using the supplier's number format.
9. `currency`: the row's currency if the supplier sends one and it is not empty, else the supplier's
   `currency` from `config/vendors.json` (available as `self.settings["currency"]`).
10. `due_date`: the row's due date if the supplier sends one and it is not empty, else the invoice
    date plus the supplier's `terms_days` (`self.default_due(invoice_date)`).
11. `invoice_id` and `line_no` are kept as the supplier wrote them, stripped (`line_no` as `int`).
