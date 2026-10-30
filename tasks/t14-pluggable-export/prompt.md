`exportkit.export()` turns a list of records (dicts) into CSV, JSON or a text table. It works, but
everything is in one tangled function in `exportkit/export.py`, and adding an output format means
editing that function. Refactor it into layers with pluggable output formats.

**Behaviour must not change.** R1 to R8 describe what `export()` does today, exactly; all of it
must still hold afterwards. R9 to R12 describe the structure to build.

1. `export(records, fmt, columns=None, sort_by=None, descending=False, limit=None)` returns a `str`.
   `fmt` is `"csv"`, `"json"` or `"table"`; any other value raises `ValueError` whose message is
   `unknown format` followed by the repr of the value (`unknown format 'xml'`). Problems are
   reported in this order, and only the first one is raised: the format, then the columns (R2),
   then `sort_by` (R3), then `limit` (R4). `export` never modifies `records`.
2. Columns. With `columns=None` they are all the keys that appear in `records`, in the order they
   are first seen (records in order, each record's keys in its own order). Otherwise they are
   exactly the names given, in that order (any iterable of names). A record that lacks a column has
   `None` there. A name that appears twice in `columns` raises `ValueError("duplicate column 'a'")`
   (the first repeated name).
3. Sorting. `sort_by` must be one of the columns, otherwise `ValueError("unknown sort column 'x'")`.
   Rows whose value in that column is `None` always come last, in their original order, whether
   `descending` is true or not. The other rows are ordered by that value: `int`, `float` and `bool`
   values compare as numbers (`True` is 1), every other value compares as `str(value)`, and all
   numbers come before all strings when ascending. `descending=True` reverses that order (strings
   first). Rows with equal values keep their original relative order in both directions.
4. `limit`: after sorting, only the first `limit` rows are kept; `limit=0` keeps none. A negative
   or non-`int` limit (a `bool` counts as invalid) raises `ValueError("limit must be a non-negative
   int")`.
5. CSV: a header line with the column names, then one line per row, cells joined with `,`. Every
   line, the last one too, ends with `"\n"`. Cell text: `None` is empty, `True` is `true`, `False`
   is `false`, a `float` is written with two decimals and then trailing zeros and a trailing `.`
   are removed (`3.14159` gives `3.14`, `10.0` gives `10`, `2.5` gives `2.5`), anything else is
   `str(value)`. A cell that contains `,`, `"`, a carriage return or a line feed, or that begins or
   ends with a space, is wrapped in double quotes with every inner `"` doubled. Column names in the
   header follow the same rules. With no columns the result is the empty string.
6. JSON: a JSON array with one object per row, keys in column order, produced like
   `json.dumps(objects, indent=2, ensure_ascii=False)`. Values are not changed (floats are not
   rounded, `None` is `null`), and there is no trailing newline. With no rows the result is `[]`.
7. Table: a header line with the column names, a separator line, then one line per row. Cells
   within a line are separated by two spaces and padded to the width of their column (the longest
   of the header and the cells). The separator line has `-` repeated to each column's width,
   joined by two spaces. Trailing whitespace is removed from the header and row lines. Cell text:
   `None` is `-`, `True` is `yes`, `False` is `no`, a `float` is written with exactly two decimals
   (`3.0` gives `3.00`), anything else is `str(value)`. A column is right-aligned when it has at
   least one non-`None` value and every non-`None` value is an `int` or `float` (not a `bool`); all
   other columns are left-aligned, and the header cell is aligned like the column. Lines are joined
   with `"\n"` and there is no trailing newline.
8. When there are no columns (no records, or records without any keys and `columns=None`): CSV is
   `""`, the table is `(no data)`, and JSON has one `{}` per record (so `[]` for no records). With
   columns but no rows: CSV is just the header line, JSON is `[]`, the table is the header and
   separator lines.
9. New module `exportkit.rows` with `prepare(records, columns=None, sort_by=None, descending=False,
   limit=None)`, which returns `(columns, rows)`: `columns` is a list of the column names and `rows`
   a list with one list of raw (unformatted) values per record, in column order, already sorted
   and limited. It applies R2 to R4, including their errors, and knows nothing about formats.
10. New module `exportkit.formats` with a registry of output formats. A renderer is a callable
    `renderer(columns, rows) -> str` that receives what `prepare` returns.
    `register(name, renderer, replace=False)` adds one; it raises `ValueError` if `name` is not a
    non-empty `str` or is already registered (unless `replace=True`), and `TypeError` if `renderer`
    is not callable. `unregister(name)` removes one (`KeyError` if it is not registered).
    `names()` returns the registered names as a sorted list. `get(name)` returns the renderer; for
    an unknown name it raises `UnknownFormatError`, a subclass of `ValueError` with the message of
    R1, which `exportkit` also exports (`from exportkit import UnknownFormatError`).
11. `"csv"`, `"json"` and `"table"` are registered when `exportkit.formats` is imported, with
    renderers that follow R5 to R8: for any `records`, `get("csv")(*prepare(records))` equals
    `export(records, "csv")`, and likewise for the other two.
12. `export()` looks the format up in the registry each time it is called (so a format registered
    later, or a built-in replaced with `replace=True`, is used at once), then calls `prepare`, then
    calls the renderer once with the `(columns, rows)` that `prepare` returned, and returns the
    string the renderer returned. The lookup comes first, so R1's error order still holds.

`from exportkit import export` keeps working. Use only the Python standard library. Existing tests
are in `tests/`.
