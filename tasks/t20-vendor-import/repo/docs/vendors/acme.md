# Acme export

Comma-separated, header line, UTF-8. Columns: `invoice`, `line`, `sku`, `desc`, `qty`,
`unit_price` (dot decimal, comma thousands, e.g. `1,234.50`), `currency`, `date` and `due`
(both `YYYY-MM-DD`; `due` may be empty). Acme never cancels lines; it issues credit notes instead.
