# Corvid GmbH: Rechnungsexport v2 (notes for customers)

Our invoice export is a UTF-8 text file (with BOM), semicolon-separated, one invoice position per
line, with a header line. Fields may be quoted with double quotes.

| Column | Meaning | Format |
|---|---|---|
| `Rechnung` | invoice number | text, e.g. `R-2024-0117` |
| `Pos` | position on the invoice | whole number |
| `Artikel` | article number | text; we print it with spaces and dashes for readability, e.g. `CV-10 220` |
| `Bezeichnung` | description | text |
| `Menge` | quantity | whole number |
| `Einzelpreis` | unit price | German format: decimal comma, `.` between thousands, e.g. `1.234,50`; at most 2 decimals |
| `Waehrung` | currency | ISO code; empty means your account currency |
| `Datum` | invoice date | `DD.MM.YYYY` |
| `Faellig` | due date | `DD.MM.YYYY`; empty means our standard payment terms apply |
| `Status` | position status | `OK`, or `STORNO` for a cancelled position |

Cancelled positions stay in the export so the invoice numbering has no gaps.
