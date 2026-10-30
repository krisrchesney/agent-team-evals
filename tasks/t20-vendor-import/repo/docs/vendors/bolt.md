# Bolt export

Tab-separated, header line, UTF-8 with BOM. Columns: `InvoiceNo`, `LineNo`, `Part`, `Text`, `Qty`,
`PriceCents` (an integer number of cents), `InvDate` and `DueDate` (`MM/DD/YYYY`; `DueDate` may be
empty), `State` (`open`, `paid` or `cancelled`). No currency column: everything is billed in the
account currency.
