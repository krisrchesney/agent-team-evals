# t37-mini-sql: where each hidden-test rule is shown

Every rule is written in `repo/docs/SPEC.md` (the prompt points to it); the tree classes in `ast.py` and
the CSV typing rules in `catalog.py` are given. This file is outside `repo/`, so agents never see it.

| Test group | Rule | SPEC.md section |
|---|---|---|
| `TestParse` precedence, BETWEEN, predicate forms | operator levels, left grouping, `BETWEEN ... AND` is not a logical AND, `NOT` weaker than comparison, `<>` stored as `!=` | Syntax |
| `test_literals`, `test_names_case_and_item_text`, `test_star_items` | literal folding of `-5`, `''` escape, lower-cased names, upper-cased functions, `SelectItem.text` and alias spelling, `COUNT(*)` shape | Syntax |
| `test_all_clauses`, `test_syntax_errors_and_positions` | clause grammar incl. `LEFT OUTER`, optional `AS`, comments, `;`; `ParseError.pos` rules (unterminated string at the quote, end of text, chained comparisons, `OFFSET` without `LIMIT`, extra statement) | Syntax |
| `TestSelectBasics` | output names (header spelling, alias, source text), CSV typing, three-valued WHERE, boolean values 1/0/NULL, arithmetic types and `/` by zero, `IN` with NULLs, `LIKE` (case, whole string, literal `.`), `BETWEEN`, functions incl. `ROUND` half away from zero, function and type errors, aliases hidden from WHERE | Values and operators, Select list |
| `TestJoins` | inner and left join, row order, `ON` versus `WHERE` for left joins, self and three-way joins, `ON` sees only earlier tables, ambiguity and unknown names, alias hides table name, duplicate alias, `*` and `t.*` | Tables, aliases, columns; Joins |
| `TestGrouping` | groups in first-appearance order incl. NULL group, `COUNT` forms, aggregates over no rows (one row without GROUP BY, none with), SUM/AVG types, DISTINCT aggregates, strings in MIN/MAX, HAVING rules, the `must appear in GROUP BY` errors (also for empty tables and ORDER BY/HAVING), expression matching after resolution, grouping over joins, `COUNT(col)` vs `COUNT(*)` on a left join | Aggregates and grouping |
| `TestOrderingAndLimits` | NULL order, stability in both directions, positions, aliases (alias beats column), expressions, aggregates in ORDER BY, mixed-type sort error, DISTINCT after ORDER BY then LIMIT/OFFSET | ORDER BY, DISTINCT, LIMIT |

What makes it hard: it is a small database engine written from a 130-line spec. Parser, join, NULL logic,
grouping validation and ordering all interact, and the spec is explicit about many places where a simple
Python implementation differs (stable DESC sort, NULL placement, `IN` with NULL, `BETWEEN`'s `AND`,
`HAVING`/`ORDER BY` with aggregates that are not selected, `ON` scoping, `ROUND` rounding).
