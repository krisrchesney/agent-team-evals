# minisql spec

`query(sql, catalog)` = `execute(parse(sql), catalog)`. `execute` returns `Result(columns, rows)`:
`columns` is a list of output names, `rows` a list of tuples of `int`, `float`, `str` or `None` (NULL).
Boolean results are the ints `1` and `0`. Errors are `ParseError` (bad syntax), `QueryError` (cannot be run)
and `CatalogError` (table problems from `catalog.py`; `execute` lets them through).

## Syntax (`parse`)

    SELECT [DISTINCT] item [, item ...]
    FROM table [[AS] alias]
    [ [INNER | LEFT [OUTER]] JOIN table [[AS] alias] ON expr ] ...
    [WHERE expr] [GROUP BY expr [, expr ...]] [HAVING expr]
    [ORDER BY expr [ASC | DESC] [, ...]] [LIMIT n [OFFSET m]] [;]

- Keywords are case-insensitive. Reserved words (not usable as names): SELECT DISTINCT FROM WHERE GROUP BY
  HAVING ORDER ASC DESC LIMIT OFFSET JOIN INNER LEFT OUTER ON AS AND OR NOT IS NULL IN LIKE BETWEEN TRUE FALSE.
- Names are letters, digits and `_`, not starting with a digit. They are stored lower-cased in the tree.
- Items: `*`, `name.*`, or `expr [AS alias]` (`AS` is required for an item alias; a table alias may omit it).
  `SelectItem.alias` keeps the spelling after `AS`; `SelectItem.text` is the exact source text of the item,
  from its first character to its last (no surrounding whitespace or comma); for `*` it is `*` or `t.*`.
- Literals: integers `12`, decimals `3.5` (digits, a dot, digits), strings `'it''s'` (a doubled quote is a
  quote), `NULL`, `TRUE`, `FALSE` (the ints 1 and 0). A `-` directly before a numeric literal in a unary
  position is folded into the literal: `-5` is `Literal(-5)` and `- x` is `Unary("-", Column)`.
- A column is `name` or `table.name`.
- Operators, tightest first: unary `-`; `*` `/`; `+` `-`; comparisons `=` `!=` `<>` `<` `<=` `>` `>=` and
  `IS [NOT] NULL`, `[NOT] IN (a, b, ...)`, `[NOT] LIKE x`, `[NOT] BETWEEN a AND b`; `NOT`; `AND`; `OR`.
  Binary operators of one level group to the left. `<>` is stored as `"!="`. Comparisons do not chain
  (`a < b < c` is a `ParseError`). The operands of `BETWEEN` are additive expressions, so its own `AND` is
  not a logical `AND` (`x BETWEEN 1 AND 5 AND y` is `(x BETWEEN 1 AND 5) AND y`). `NOT` binds weaker than
  comparison: `NOT a = b` is `NOT (a = b)`.
- Function call: `name(expr, ...)`, `name(DISTINCT expr)`, `COUNT(*)` (stored as `Func("COUNT", (), star=True)`).
  Names are stored upper-cased.
- `LIMIT` and `OFFSET` take non-negative integer literals. `OFFSET` needs `LIMIT`.
- Anything else is a `ParseError` whose `pos` is the 0-based offset of the offending token (the end of the
  text for an unexpected end; the opening quote for an unterminated string; the character for an unknown
  character). Text after the statement (and its optional `;`) is a `ParseError` at the first extra token.
- `--` starts a comment that runs to the end of the line.

## Execution (`execute`)

### Tables, aliases, columns
Each table comes from `catalog.table(name)`. Its alias is the explicit alias, or its own name; once a table
has an alias its name no longer works as a qualifier. Two tables with the same alias or name (a self join
needs aliases) is a `QueryError`. A column reference matches columns by lower-cased name; `t.c` also needs
the alias `t`. Zero matches, an unknown alias, or more than one match (an unqualified name that exists in two
tables) is a `QueryError`. The `ON` of a join can see only the tables up to and including that join's table;
every other clause sees all tables.

### Joins
Rows are combined left to right, in order: for each row so far, the joined table's rows in file order.
`INNER` keeps pairs where `ON` is true. `LEFT` also keeps a left row that has no true pair, once, with NULL
for every column of the joined table. `ON` is a condition (see Truth). `ON`, `WHERE` and `GROUP BY` may not
contain aggregates (`QueryError`).

### Values and operators
- NULL: any arithmetic or comparison with NULL gives NULL, as do `LIKE` and `BETWEEN` with a NULL operand
  (see below), and functions given NULL (except `COALESCE`).
- Numbers compare numerically (`2 = 2.0` is true); strings compare by code point, case-sensitively. Comparing
  a number with a string is a `QueryError` (when neither side is NULL). Arithmetic on a string is a `QueryError`.
- `+ - *` give an int for two ints, else a float. `/` always gives a float, and is NULL when the divisor is 0.
- Truth: a value used as a condition is true if it is a non-zero number, false for 0, NULL for NULL, and a
  `QueryError` for a string. `AND`, `OR`, `NOT` use three-valued logic (`false AND NULL` is false, `true OR NULL`
  is true, `NOT NULL` is NULL, otherwise NULL when an operand is NULL) and give 1, 0 or NULL. `WHERE`, `ON` and
  `HAVING` keep only rows (groups) whose condition is true.
- `x IS NULL` / `IS NOT NULL` give 1 or 0, never NULL.
- `x IN (a, b, ...)`: NULL if `x` is NULL; else 1 if some item equals `x` (items are compared in order and the
  search stops at the first equal one); else NULL if some item is NULL; else 0. `NOT IN` is the three-valued
  negation of that.
- `x LIKE p`: both must be strings (else NULL if either is NULL, `QueryError` if a non-NULL one is not a string).
  `%` matches any run of characters (also none), `_` exactly one, everything else literally, ignoring the
  case of ASCII letters. The whole string must match. `NOT LIKE` negates (NULL stays NULL).
- `x BETWEEN a AND b` is `x >= a AND x <= b` (three-valued); `NOT BETWEEN` is its negation.
- Scalar functions (wrong argument count or unknown name is a `QueryError`): `UPPER(s)`, `LOWER(s)`, `LENGTH(s)`
  (characters; strings only); `ABS(n)` (keeps int or float); `COALESCE(a, b, ...)` (two or more arguments; the
  first non-NULL one, else NULL); `ROUND(x)` and `ROUND(x, n)` (`n` a non-negative int literal, default 0): a
  float, rounded half away from zero, computed with `decimal.Decimal(repr(float(x)))` and `ROUND_HALF_UP`
  (so `ROUND(2.5)` is `3.0`, `ROUND(-2.5)` is `-3.0`, `ROUND(1.005, 2)` is `1.01`).

### Aggregates and grouping
- Aggregates: `COUNT(*)` (rows in the group), `COUNT(x)` (non-NULL values), `COUNT(DISTINCT x)`, `SUM(x)`,
  `AVG(x)`, `MIN(x)`, `MAX(x)`, and `SUM(DISTINCT x)`, `AVG(DISTINCT x)`. They skip NULL values. `COUNT`
  gives 0 for no values; `SUM`, `AVG`, `MIN`, `MAX` give NULL for no values. `SUM` of ints is an int, of any
  float a float; `AVG` is a float. `SUM` and `AVG` of a string are a `QueryError`; `MIN`/`MAX` work on numbers
  or on strings (a mix is a `QueryError`). `DISTINCT` and `*` are only allowed where listed; the argument of an
  aggregate may not contain an aggregate.
- A query is an *aggregate query* if it has `GROUP BY` or any aggregate in the select items, `HAVING` or
  `ORDER BY`. `HAVING` in a query that is not an aggregate query is a `QueryError`.
- Groups: rows are grouped by the values of the `GROUP BY` expressions (NULLs form one group; `1` and `1.0`
  are one group) and the groups are kept in order of first appearance. Without `GROUP BY` there is one group
  holding all rows, even when there are none (so `SELECT COUNT(*) FROM t` on an empty table gives one row,
  `0`). With `GROUP BY` and no rows there are no groups.
- In an aggregate query, every select item, `HAVING` term and `ORDER BY` term must be built only from
  aggregates, literals and expressions that match a `GROUP BY` expression; any other column reference
  is a `QueryError` (even if the table is empty). An expression matches a `GROUP BY` expression when the
  two are the same after column references are resolved (`x` and `t.x` match; `a + 1` matches `A+1`).
  An expression that matches is evaluated once per group (on the group's first row).

### Select list and output names
`*` expands to every column of every table, in FROM/JOIN order, `t.*` to that table's columns (an unknown
alias is a `QueryError`). Output names: the alias, if there is one (as written after `AS`); else for a column
reference the column's name as spelled in the CSV header; else `SelectItem.text`; for `*` the header names.
Duplicate output names are fine.

### ORDER BY, DISTINCT, LIMIT
- An `ORDER BY` term that is an integer literal is a 1-based position in the select list (out of range is a
  `QueryError`). An unqualified name equal (ignoring case) to a select-item alias is that output column.
  Anything else is an expression evaluated like a select item (in a non-aggregate query it may use columns
  that are not selected).
- NULL sorts before every value ascending and after every value descending. The sort is stable (ties keep the
  earlier order); with several terms the first is the most significant. Comparing a number with a string in
  the sort is a `QueryError`.
- Order of steps: join, `WHERE`, grouping, `HAVING`, select list, `ORDER BY`, then `DISTINCT` (keeps the
  first of equal rows, in sorted order), then `OFFSET` and `LIMIT`.
