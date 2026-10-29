`csvreport` is a small command-line tool that groups the rows of a CSV file and totals one column:

    python -m csvreport sales.csv --group-by region --sum amount

It prints a CSV report to stdout: a header line `region,sum_amount`, then one line per group,
sorted by group name. The code is split into `reader.py` (parsing the file), `aggregate.py`
(grouping), `render.py` (the report text) and `cli.py` (arguments; `main(argv) -> int`).
Extend it so that:

1. A new option `--agg {sum,count,mean,min,max}` (default `sum`) picks the aggregation, and a new
   option `--value COL` names the column to aggregate. `--sum COL` keeps working and means
   `--agg sum --value COL`. Giving `--sum` together with `--agg` or `--value` is a usage error.
   `--value` (or `--sum`) is required for every aggregation except `count`, which counts the rows
   in each group and ignores `--value`. Leaving it out otherwise is a usage error.
2. The report header is `<group-by>,<agg>_<value>` (for example `region,mean_amount`), or
   `<group-by>,count` for count. Counts print as integers; every other value prints with exactly
   two decimals (`12.50`). Groups stay sorted by group name.
3. Header names and cell values have leading and trailing whitespace stripped before they are
   used. A row whose cells are all empty is skipped entirely (it is not counted).
4. An empty value cell is not an error: that row is left out of sum, mean, min and max (it is
   still counted by `count`). A group with no non-empty values is still listed; its value is
   `0.00` for sum and an empty field for mean, min and max.
5. A value cell that is not empty and is not a number (as Python's `float()` reads it) is an
   error. Print `csvreport: error: <path>:<line>: bad number '<cell>' in column '<col>'` to
   stderr, where `<path>` is the path as given on the command line and `<line>` is the 1-based
   line number in the file (the header is line 1; blank lines count). Exit with status 2 and print
   nothing to stdout. If there are several bad cells, report the first one in the file.
6. If the `--group-by` column, the value column or a `--where` column is not in the header,
   print `csvreport: error: no column '<name>'` to stderr and exit with status 2.
7. A new repeatable option `--where COL=VALUE` keeps only rows whose (stripped) `COL` cell equals
   `VALUE` exactly. Split the argument on the first `=`. With several `--where` options a row must
   match all of them. Rows that are filtered out are not checked for bad numbers.
8. A new option `--delimiter CHAR` (default `,`) sets the delimiter used to read the input. The
   report itself is always comma-separated.
9. Report fields that contain a comma, a double quote or a newline are quoted the way Python's
   `csv` module quotes them by default (`"North, East"`, `"say ""hi"""`).
10. `main()` returns 0 on success and exits with status 2 on any error above. Usage errors may
    exit through argparse (`SystemExit` with code 2).

Standard library only. Existing tests are in `tests/`.
