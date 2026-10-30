`salesrep` reads a CSV of sales transactions and prints a revenue report
(`python -m salesrep FILE`). The package is a pipeline: `parse.py` reads rows, `validate.py` applies
business rules, `transform.py` prices each row in USD (`fx.py` holds the rates), `aggregate.py`
groups the rows, `render.py` and `export.py` draw the table and the JSON, `report.py` ties it
together and `cli.py` is the command line. This task adds several features that cut across these
modules. Every rule below is numbered (R1, R2, ...) and every number is a rule you must follow.
Where the report has to look exactly right, the text says exactly how.

**Things that look odd but are meant, and must not change.** The discount comes off the unit price
and the discounted unit price is rounded half up to cents before it is multiplied by the quantity;
the USD amount of each row is then rounded half up to cents on its own (R1). Region and product names
are tidied (ends stripped, runs of whitespace squeezed to one space) and grouped case-insensitively;
a group is labelled with the first spelling seen, and groups are listed sorted by label,
case-insensitively (R2). Rows with status `void` are valid rows that are dropped silently: they
are not counted anywhere and are not reported as skipped (R3). When rows were skipped, the table
report ends with a blank line and then `Skipped N invalid rows`, and it says `rows` even when N is 1
(R4). The `--json` option keeps working and keeps its shape: an object with `rows` and `total`,
each having `group`, `orders`, `units` and `revenue`, where `revenue` is a string with exactly two
decimals (R5). The table keeps its present layout rules: the first column is left-aligned, the others
are right-aligned, every column is as wide as its longest cell with the header counted, columns are
separated by two spaces, and a dashed rule sits under the header and above the `TOTAL` line (R6).

**Grouping.** A new option `--by` takes `region` (the default), `product` or `month`. The first
column header is the capitalised name (`Region`, `Product`, `Month`) (R7). Products are tidied and
grouped exactly as regions are (R8). A month group is labelled `YYYY-MM` from each row's own date
and the groups are listed in calendar order (R9).

**Refunds.** `refunded` becomes a valid status. A refunded row is priced exactly like a paid row
and then counted as negative: its USD amount is subtracted from the group's revenue and its quantity
is subtracted from the group's units, but it does not count as an order (R10). Because of that a group can have
negative revenue, negative units, or no orders at all; units are always printed as plain integers
such as `-3` (R11).

**New columns and number formats in the table.** After `Revenue` the table gets `Avg Order` and
`Share`, in that order. `Avg Order` is the group's revenue divided by its number of orders, rounded half
away from zero to cents and written as money; when the group has no orders it is a single `-`
(R12). `Share` is the group's revenue as a percent of the total revenue, rounded half away from zero to
one decimal and written with a percent sign (`12.5%`); a negative share has a leading minus (`-3.2%`)
(R13). If the total revenue is exactly zero, every share, the total's included, is `0.0%` (R14).
The `TOTAL` line's share is `100.0%` otherwise, and its average is computed like any other group's
(R15). In the table, money amounts (`Revenue` and `Avg Order`) are written with thousands separators and
two decimals, and a negative amount is written in parentheses with no minus sign, as in `(1,234.50)`
(R16). A negative zero is never shown: money that rounds to zero is `0.00` and a share that rounds to
zero is `0.0%`, whatever the sign of the underlying number (R17).

**Top N.** `--top N` keeps only the N groups with the most revenue, listed from the highest revenue
down, ties broken by label ascending (plain, case-sensitive string comparison) (R18). All other groups
are merged into one trailing row labelled `Other` that adds up their orders, units and revenue;
its average and share are worked out from those sums, like any group's (R19). The `TOTAL` line and every share
still refer to all groups, kept or merged (R20). If there are no more than N groups there is no
`Other` row, but the rows are still in highest-revenue-first order (R21). `N` must be a whole number
of at least 1; otherwise print `salesrep: error: --top must be a whole number of at least 1` to
stderr and exit with status 2 (R22).

**Labels, title, formats.** In the table only, a group label longer than 20 characters is shown as its
first 17 characters followed by `...`, and column widths follow the labels as shown (R23). The option
`--title TEXT` prints the text on the line above the header, with `(table width - title length) // 2`
spaces in front and no trailing spaces, where the table width is the length of the dashed rule; a title
wider than the table is printed with no padding (R24). `--format` takes `table` (the default), `csv` or
`json`; `--json` means `--format json`, and giving both is an error: `salesrep: error: use either --json
or --format`, status 2 (R25). The CSV output has the header `group,orders,units,revenue,avg_order,share`,
one line per row in the same order as the table (the `Other` row included), then a final `TOTAL` line.
Its revenue and avg_order are plain numbers with two decimals and a minus sign when negative (`-1234.50`,
no separators, no parentheses), avg_order is empty when there are no orders, share has one decimal and no
percent sign, labels are never shortened, and fields are quoted only when the `csv` module's defaults
would quote them; lines end with `\n` and there is no title (R26). The JSON output keeps R5's shape and
gives every row and the total two more keys: `avg_order` (a two-decimal string, or `null` when there
are no orders) and `share` (a one-decimal string without a percent sign); `revenue` and `avg_order` use
the CSV number style, labels are never shortened, and the rows come in the table's order (R27). With
`--format csv` or `json` the skipped-rows text is printed to stderr instead of stdout, as the same block
the table would end with, without the blank line before it (R28).

**Skipped rows in detail.** Under `Skipped N invalid rows` the table report now lists the reasons, one
line each, in file order, written as two spaces then `Line L: message` (`L` is the 1-based line in the
file, the header being line 1, blank lines counted). At most 5 reasons are listed; if there are more,
a last line `  ... and K more` says how many were left out (R29).

**More validation.** A row is rejected as `duplicate id 'X'` when an earlier row with the same id
was accepted, meaning it passed every other rule (void and refunded rows are accepted rows, rows rejected
for any other reason do not use up their id); this is checked after all the other rules, and before any
date window or grouping is applied (R30). The currencies `CAD` (rate 0.74) and `JPY` (rate 0.0067) are
added. A JPY unit price must be a whole number, otherwise the row is rejected with `price must be a whole
number for JPY`; that rule comes after the unknown-currency rule and before the status rule (R31).

**Date window and exit status.** `--from DATE` and `--to DATE` (`YYYY-MM-DD`) keep only the rows dated
on or after, respectively on or before, that day, ends included (R32). The window is applied after
validation: rows rejected by the rules are still listed as skipped whatever their date, and only the
accepted rows are filtered (R33). A date that is not a valid `YYYY-MM-DD` date prints
`salesrep: error: bad date 'TEXT' for --from` (or `--to`) to stderr and exits with 2; `--from` later than
`--to` prints `salesrep: error: --from is after --to` and exits with 2 (R34). `--strict` makes the exit
status 1 when any row was skipped, after printing the report as usual; without it a report that skipped
rows still exits 0. Input and option errors exit 2 (R35).

**Reasons that already exist.** Cells are stripped of surrounding whitespace before use, a currency code is upper-cased and
a status is lower-cased, and an empty optional cell means a discount of `0`, the currency `USD` and the status `paid`. A required
column that is missing from the header stops the run with `salesrep: error: missing column 'NAME'` (the first missing one in the order
id, date, region, product, qty, unit_price) on stderr and status 2. A row the parser cannot use is skipped with one of
`missing value for 'COLUMN'` (a required cell is empty), `bad date 'TEXT'`, `bad quantity 'TEXT'`, `bad price 'TEXT'` or
`bad discount 'TEXT'`. The business rules are checked in this order and the first one that fails gives the reason:
`id longer than 20 characters`, `region or product longer than 40 characters`, `qty must be positive`,
`price must not be negative`, `discount must be between 0 and 100`, `unknown currency 'CODE'`, then the JPY rule (R31),
`unknown status 'TEXT'`, and last the duplicate-id rule (R30). All of these keep working as they do today (R36).

Standard library only. Existing tests are in `tests/`.
