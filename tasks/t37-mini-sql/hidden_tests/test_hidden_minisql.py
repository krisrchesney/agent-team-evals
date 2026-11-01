"""Hidden tests for t37-mini-sql. Every rule is in docs/SPEC.md; see AUDIT.md."""
import os
import tempfile
import unittest

from minisql import Catalog, CatalogError, ParseError, QueryError, parse, query
from minisql.ast import (Between, Binary, Column, Func, InList, IsNull, Like, Literal, TableRef, Unary)

EMPLOYEES = """id,name,dept_id,salary,manager_id
1,Ann,1,100,
2,Bob,1,80,1
3,Cy,2,90,1
4,Di,2,,3
5,Ed,,70,3
6,Flo,3,60,2
"""
DEPARTMENTS = """id,name,city
1,Eng,Paris
2,Ops,Rome
3,Sales,Paris
4,Legal,Oslo
"""
FILES = {
    "employees.csv": EMPLOYEES,
    "Departments.csv": DEPARTMENTS,
    "mixed.csv": "ID,Label\n1,x\n",
    "scores.csv": "k,x\na,1.5\na,2\nb,\n",
    "nums.csv": "n\n1\n1\n2\n",
    "codes.csv": "code,label\n007,x\n010,y\n",
}


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        for name, text in FILES.items():
            with open(os.path.join(cls._tmp.name, name), "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
        cls.catalog = Catalog(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def q(self, sql):
        return query(sql, self.catalog)

    def rows(self, sql):
        return self.q(sql).rows

    def ids(self, sql):
        return [r[0] for r in self.rows(sql)]

    def bad(self, sql, exc=QueryError):
        with self.assertRaises(exc, msg=sql):
            self.q(sql)


def col(name, table=None):
    return Column(table, name)


class TestParse(unittest.TestCase):
    def expr(self, text, where=False):
        q = parse("SELECT a FROM t WHERE %s" % text) if where else parse("SELECT %s FROM t" % text)
        return q.where if where else q.items[0].expr

    def test_arithmetic_precedence_and_associativity(self):
        self.assertEqual(self.expr("1 + 2 * 3"), Binary("+", Literal(1), Binary("*", Literal(2), Literal(3))))
        self.assertEqual(self.expr("a - b - c"), Binary("-", Binary("-", col("a"), col("b")), col("c")))
        self.assertEqual(self.expr("(1 + 2) * 3"), Binary("*", Binary("+", Literal(1), Literal(2)), Literal(3)))

    def test_logic_precedence(self):
        self.assertEqual(self.expr("a OR b AND NOT c = 1", where=True),
                         Binary("OR", col("a"), Binary("AND", col("b"), Unary("NOT", Binary("=", col("c"), Literal(1))))))

    def test_between_has_its_own_and(self):
        self.assertEqual(self.expr("x BETWEEN 1 AND 5 AND y", where=True),
                         Binary("AND", Between(col("x"), Literal(1), Literal(5), False), col("y")))
        self.assertEqual(self.expr("x NOT BETWEEN a + 1 AND 5", where=True),
                         Between(col("x"), Binary("+", col("a"), Literal(1)), Literal(5), True))

    def test_predicate_forms(self):
        self.assertEqual(self.expr("x NOT IN (1, 'a')", where=True), InList(col("x"), (Literal(1), Literal("a")), True))
        self.assertEqual(self.expr("x NOT LIKE 'a%'", where=True), Like(col("x"), Literal("a%"), True))
        self.assertEqual(self.expr("t.x IS NOT NULL", where=True), IsNull(col("x", "t"), True))
        self.assertEqual(self.expr("x <> 1", where=True), Binary("!=", col("x"), Literal(1)))

    def test_literals(self):
        q = parse("SELECT -5, - x, 2 - -3, 'it''s', 2.50, NULL, TRUE, FALSE FROM t")
        self.assertEqual([i.expr for i in q.items],
                         [Literal(-5), Unary("-", col("x")), Binary("-", Literal(2), Literal(-3)), Literal("it's"),
                          Literal(2.5), Literal(None), Literal(1), Literal(0)])

    def test_names_case_and_item_text(self):
        q = parse("SELECT Emp.Name AS Who, COUNT(*), upper( Emp.Name )  FROM Employees Emp")
        self.assertEqual((q.items[0].expr, q.items[0].alias, q.items[0].text), (col("name", "emp"), "Who", "Emp.Name"))
        self.assertEqual((q.items[1].expr, q.items[1].alias, q.items[1].text), (Func("COUNT", (), False, True), None,
                                                                                 "COUNT(*)"))
        self.assertEqual((q.items[2].expr, q.items[2].text), (Func("UPPER", (col("name", "emp"),)), "upper( Emp.Name )"))
        self.assertEqual(q.table, TableRef("employees", "emp"))

    def test_star_items(self):
        q = parse("SELECT *, T.* FROM t")
        self.assertEqual([(i.star, i.star_table, i.text, i.expr) for i in q.items],
                         [(True, None, "*", None), (True, "t", "T.*", None)])

    def test_all_clauses(self):
        q = parse("select distinct a, b from t1 x inner join t2 on x.a = t2.a left outer join t3 as z on z.a <> 1 "
                  "join t4 on 1 where a > 1 group by a, b having count(*) > 1 order by a desc, b asc, 1 "
                  "limit 5 offset 2; -- done")
        self.assertTrue(q.distinct)
        self.assertEqual([j.kind for j in q.joins], ["INNER", "LEFT", "INNER"])
        self.assertEqual(q.joins[1].table, TableRef("t3", "z"))
        self.assertEqual(q.joins[1].on, Binary("!=", col("a", "z"), Literal(1)))
        self.assertEqual(len(q.group_by), 2)
        self.assertEqual(q.having, Binary(">", Func("COUNT", (), False, True), Literal(1)))
        self.assertEqual([o.desc for o in q.order_by], [True, False, False])
        self.assertEqual((q.limit, q.offset), (5, 2))
        c = parse("select a -- note\nfrom t")
        self.assertEqual((c.items[0].text, c.limit, c.offset), ("a", None, None))

    def test_syntax_errors_and_positions(self):
        cases = [
            ("SELECT FROM t", "FROM"),
            ("SELECT a FROM", None),
            ("SELECT 'abc FROM t", "'abc"),
            ("SELECT a FROM t WHERE a < b < c", "< c"),
            ("SELECT a FROM t LIMIT 1.5", "1.5"),
            ("SELECT a FROM t OFFSET 2", "OFFSET"),
            ("SELECT a FROM t; SELECT b FROM t", "SELECT b"),
            ("SELECT a # b FROM t", "#"),
            ("SELECT a FROM t WHERE", None),
            ("SELECT a b FROM t", "b FROM"),
            ("SELECT a FROM t JOIN u", None),
            ("SELECT * FROM select", "select"),
            ("SELECT a FROM t WHERE a IN ()", ")"),
            ("SELECT SUM(*) FROM t", "*"),
            ("SELECT a FROM t ORDER a", "a"),
        ]
        for sql, needle in cases:
            with self.subTest(sql=sql):
                with self.assertRaises(ParseError) as ctx:
                    parse(sql)
                want = len(sql) if needle is None else sql.index(needle) if needle != "FROM" else sql.index("FROM")
                if sql == "SELECT a FROM t ORDER a":
                    want = sql.index("a", sql.index("ORDER"))
                self.assertEqual(ctx.exception.pos, want)


class TestSelectBasics(Base):
    def test_star_and_output_names(self):
        r = self.q("SELECT * FROM departments")
        self.assertEqual(r.columns, ["id", "name", "city"])
        self.assertEqual(r.rows[0], (1, "Eng", "Paris"))
        self.assertEqual(self.q("SELECT id, LABEL, label AS Tag FROM MIXED").columns, ["ID", "Label", "Tag"])
        r = self.q("SELECT salary * 2 AS double, salary*2, UPPER( name ) FROM employees WHERE id = 1")
        self.assertEqual(r.columns, ["double", "salary*2", "UPPER( name )"])
        self.assertEqual(r.rows, [(200, 200, "ANN")])

    def test_csv_types(self):
        self.assertEqual(self.rows("SELECT code FROM codes"), [(7,), (10,)])
        self.assertEqual(self.rows("SELECT 1 FROM employees WHERE salary > 99.5"), [(1,)])

    def test_where_three_valued(self):
        self.assertEqual(self.ids("SELECT id FROM employees WHERE salary > 75"), [1, 2, 3])
        self.assertEqual(self.ids("SELECT id FROM employees WHERE NOT salary > 75"), [5, 6])
        self.assertEqual(self.ids("SELECT id FROM employees WHERE salary = NULL"), [])
        self.assertEqual(self.ids("SELECT id FROM employees WHERE salary IS NULL"), [4])
        self.assertEqual(self.ids("SELECT id FROM employees WHERE manager_id IS NOT NULL AND dept_id IS NULL"), [5])
        self.assertEqual(self.ids("SELECT id FROM employees WHERE dept_id = 1 OR salary > 85 AND dept_id = 2"), [1, 2, 3])

    def test_boolean_logic_values(self):
        self.assertEqual(self.rows("SELECT NULL AND 0, NULL OR 1, NULL AND 1, NULL OR 0, NOT NULL, 1 AND 1, NOT 5, "
                                   "NULL IS NULL FROM departments LIMIT 1"), [(0, 1, None, None, None, 1, 0, 1)])
        self.assertEqual(self.rows("SELECT id > 2 FROM employees ORDER BY id LIMIT 3"), [(0,), (0,), (1,)])

    def test_arithmetic_and_comparisons(self):
        r = self.rows("SELECT 7 / 2, 4 / 2, 7 - 2 * 3, 5 / 0, 1 + NULL, 2 * 1.5, 2 = 2.0, 1 < 1.5, 'a' < 'b', "
                      "'B' < 'a', 'a' = 'A' FROM departments LIMIT 1")
        self.assertEqual(r, [(3.5, 2.0, 1, None, None, 3.0, 1, 1, 1, 1, 0)])
        self.assertIsInstance(r[0][1], float)
        self.assertIsInstance(r[0][2], int)

    def test_in(self):
        self.assertEqual(self.rows("SELECT 1 IN (1, NULL), 2 IN (1, NULL), 2 IN (1, 3), NULL IN (1), 2 NOT IN (1, NULL), "
                                   "2 NOT IN (1, 3), 1 NOT IN (1, NULL) FROM departments LIMIT 1"),
                         [(1, None, 0, None, None, 1, 0)])
        self.assertEqual(self.ids("SELECT id FROM employees WHERE dept_id IN (2, 3)"), [3, 4, 6])
        self.assertEqual(self.ids("SELECT id FROM employees WHERE dept_id NOT IN (2, 3)"), [1, 2])

    def test_like(self):
        self.assertEqual(self.rows("SELECT name FROM employees WHERE name LIKE '_o%'"), [("Bob",)])
        self.assertEqual(self.rows("SELECT name FROM employees WHERE name LIKE 'ANN'"), [("Ann",)])
        self.assertEqual(self.rows("SELECT name FROM employees WHERE name LIKE 'A'"), [])
        self.assertEqual(self.ids("SELECT id FROM employees WHERE name NOT LIKE '%o%'"), [1, 3, 4, 5])
        self.assertEqual(self.rows("SELECT 'a.c' LIKE 'a.c', 'abc' LIKE 'a.c', 'abcabc' LIKE 'a%c', NULL LIKE 'a', "
                                   "'a' LIKE NULL FROM departments LIMIT 1"), [(1, 0, 1, None, None)])
        self.bad("SELECT id FROM employees WHERE id LIKE '1'")

    def test_between(self):
        self.assertEqual(self.ids("SELECT id FROM employees WHERE salary BETWEEN 70 AND 90"), [2, 3, 5])
        self.assertEqual(self.ids("SELECT id FROM employees WHERE salary NOT BETWEEN 70 AND 90"), [1, 6])

    def test_scalar_functions(self):
        self.assertEqual(self.rows("SELECT UPPER(name), LOWER(name), LENGTH(name), ABS(-3), ABS(-2.5), "
                                   "COALESCE(salary, 0), COALESCE(salary, manager_id, 9), ROUND(2.5), ROUND(-2.5), "
                                   "ROUND(1.005, 2), ROUND(3), ROUND(2.345, 1), UPPER(NULL), LENGTH(NULL) "
                                   "FROM employees WHERE id = 4"),
                         [("DI", "di", 2, 3, 2.5, 0, 3, 3.0, -3.0, 1.01, 3.0, 2.3, None, None)])
        self.assertEqual(self.rows("SELECT COALESCE(salary, manager_id, 9) FROM employees WHERE id = 4"), [(3,)])

    def test_function_errors(self):
        for sql in ("SELECT FOO(1) FROM employees", "SELECT UPPER(name, name) FROM employees",
                    "SELECT COALESCE(1) FROM employees", "SELECT ROUND(1, -1) FROM employees",
                    "SELECT ROUND(1, 1.5) FROM employees", "SELECT ROUND(1, id) FROM employees",
                    "SELECT UPPER(id) FROM employees", "SELECT ABS(name) FROM employees",
                    "SELECT MIN(DISTINCT id) FROM employees", "SELECT COUNT() FROM employees",
                    "SELECT SUM(id, id) FROM employees", "SELECT LENGTH(id) FROM employees"):
            with self.subTest(sql=sql):
                self.bad(sql)

    def test_type_mismatch_errors(self):
        for sql in ("SELECT id FROM employees WHERE name = 1", "SELECT name + 1 FROM employees",
                    "SELECT id FROM employees WHERE salary > 'a'", "SELECT -name FROM employees",
                    "SELECT id FROM employees WHERE name AND 1", "SELECT id FROM employees WHERE name IN (1)"):
            with self.subTest(sql=sql):
                self.bad(sql)
        self.assertEqual(self.rows("SELECT -salary FROM employees WHERE id = 1"), [(-100,)])

    def test_aliases_are_not_visible_in_where(self):
        self.bad("SELECT salary AS pay FROM employees WHERE pay > 1")


class TestJoins(Base):
    def test_inner_join(self):
        r = self.q("SELECT e.name, d.name FROM employees e JOIN departments d ON e.dept_id = d.id ORDER BY e.id")
        self.assertEqual(r.columns, ["name", "name"])
        self.assertEqual(r.rows, [("Ann", "Eng"), ("Bob", "Eng"), ("Cy", "Ops"), ("Di", "Ops"), ("Flo", "Sales")])

    def test_left_join(self):
        r = self.rows("SELECT e.name, d.name FROM employees AS e LEFT OUTER JOIN departments AS d ON e.dept_id = d.id "
                      "ORDER BY e.id")
        self.assertEqual(r, [("Ann", "Eng"), ("Bob", "Eng"), ("Cy", "Ops"), ("Di", "Ops"), ("Ed", None), ("Flo", "Sales")])

    def test_join_row_order_without_order_by(self):
        self.assertEqual(self.rows("SELECT d.id, e.id FROM departments d JOIN employees e ON d.id = e.dept_id"),
                         [(1, 1), (1, 2), (2, 3), (2, 4), (3, 6)])
        self.assertEqual(self.rows("SELECT d.id, e.id FROM departments d LEFT JOIN employees e ON d.id = e.dept_id "
                                   "WHERE d.id > 2"), [(3, 6), (4, None)])

    def test_on_condition_versus_where_condition(self):
        self.assertEqual(self.ids("SELECT d.name FROM departments d LEFT JOIN employees e "
                                  "ON e.dept_id = d.id AND e.salary > 85 ORDER BY d.id"), ["Eng", "Ops", "Sales", "Legal"])
        self.assertEqual(self.ids("SELECT d.name FROM departments d LEFT JOIN employees e ON e.dept_id = d.id "
                                  "WHERE e.salary > 85 ORDER BY d.id"), ["Eng", "Ops"])

    def test_self_join_and_three_way_join(self):
        self.assertEqual(self.rows("SELECT e.name, m.name FROM employees e JOIN employees m ON e.manager_id = m.id "
                                   "ORDER BY e.id"), [("Bob", "Ann"), ("Cy", "Ann"), ("Di", "Cy"), ("Ed", "Cy"), ("Flo", "Bob")])
        self.assertEqual(self.rows("SELECT e.name, d.name, m.name FROM employees e JOIN departments d "
                                   "ON e.dept_id = d.id JOIN employees m ON m.id = e.manager_id ORDER BY e.id"),
                         [("Bob", "Eng", "Ann"), ("Cy", "Ops", "Ann"), ("Di", "Ops", "Cy"), ("Flo", "Sales", "Bob")])

    def test_on_sees_only_tables_joined_so_far(self):
        self.bad("SELECT 1 FROM employees e JOIN departments d ON e.dept_id = m.dept_id "
                 "JOIN employees m ON m.id = e.manager_id")
        self.bad("SELECT 1 FROM employees e JOIN departments d ON d.id = x.id")

    def test_name_resolution_errors(self):
        for sql in ("SELECT name FROM employees e JOIN departments d ON e.dept_id = d.id",
                    "SELECT id FROM employees JOIN departments ON 1 = 1", "SELECT nope FROM employees",
                    "SELECT x.id FROM employees", "SELECT employees.id FROM employees e",
                    "SELECT e.id FROM employees e JOIN employees e ON 1 = 1",
                    "SELECT 1 FROM employees JOIN employees ON 1 = 1", "SELECT id FROM employees e, departments d"):
            with self.subTest(sql=sql):
                with self.assertRaises((QueryError, ParseError)):
                    self.q(sql)
        self.bad("SELECT 1 FROM employees e JOIN departments d ON d.id = e.dept_id WHERE e.id.x = 1", ParseError)

    def test_unknown_table_is_a_catalog_error(self):
        self.bad("SELECT 1 FROM nope", CatalogError)

    def test_star_with_joins(self):
        r = self.q("SELECT d.* FROM employees e JOIN departments d ON e.dept_id = d.id WHERE e.id = 1")
        self.assertEqual((r.columns, r.rows), (["id", "name", "city"], [(1, "Eng", "Paris")]))
        r = self.q("SELECT * FROM employees e JOIN departments d ON e.dept_id = d.id WHERE e.id = 1")
        self.assertEqual(r.columns, ["id", "name", "dept_id", "salary", "manager_id", "id", "name", "city"])
        self.assertEqual(r.rows, [(1, "Ann", 1, 100, None, 1, "Eng", "Paris")])
        self.bad("SELECT x.* FROM employees")


class TestGrouping(Base):
    def test_group_by_in_order_of_first_appearance(self):
        self.assertEqual(self.rows("SELECT dept_id, COUNT(*), SUM(salary), AVG(salary), MIN(salary), MAX(name) "
                                   "FROM employees GROUP BY dept_id"),
                         [(1, 2, 180, 90.0, 80, "Bob"), (2, 2, 90, 90.0, 90, "Di"), (None, 1, 70, 70.0, 70, "Ed"),
                          (3, 1, 60, 60.0, 60, "Flo")])

    def test_count_forms(self):
        self.assertEqual(self.rows("SELECT COUNT(*), COUNT(salary), COUNT(DISTINCT dept_id), COUNT(manager_id) "
                                   "FROM employees"), [(6, 5, 3, 5)])

    def test_aggregates_over_no_rows(self):
        self.assertEqual(self.rows("SELECT COUNT(*), SUM(salary), AVG(salary), MIN(salary), COUNT(salary) "
                                   "FROM employees WHERE id > 100"), [(0, None, None, None, 0)])
        self.assertEqual(self.rows("SELECT dept_id, COUNT(*) FROM employees WHERE id > 100 GROUP BY dept_id"), [])

    def test_sum_and_avg_types_and_distinct(self):
        r = self.rows("SELECT SUM(salary) FROM employees")
        self.assertEqual(r, [(400,)])
        self.assertIsInstance(r[0][0], int)
        self.assertEqual(self.rows("SELECT k, SUM(x), AVG(x), MIN(x) FROM scores GROUP BY k"),
                         [("a", 3.5, 1.75, 1.5), ("b", None, None, None)])
        self.assertEqual(self.rows("SELECT SUM(DISTINCT n), AVG(DISTINCT n), COUNT(DISTINCT n), SUM(n) FROM nums"),
                         [(3, 1.5, 2, 4)])
        self.bad("SELECT SUM(name) FROM employees")
        self.bad("SELECT MIN(salary), MIN(name) FROM employees GROUP BY dept_id HAVING MIN(salary + name) > 0")

    def test_min_max_on_strings_and_mixed(self):
        self.assertEqual(self.rows("SELECT MIN(name), MAX(name) FROM employees"), [("Ann", "Flo")])
        self.bad("SELECT MIN(COALESCE(salary, name)) FROM employees")

    def test_having(self):
        self.assertEqual(self.rows("SELECT dept_id, COUNT(*) AS n FROM employees GROUP BY dept_id HAVING COUNT(*) > 1"),
                         [(1, 2), (2, 2)])
        self.assertEqual(self.rows("SELECT dept_id FROM employees GROUP BY dept_id "
                                   "HAVING dept_id IS NOT NULL AND SUM(salary) > 100"), [(1,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM employees HAVING COUNT(*) > 10"), [])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM employees HAVING COUNT(*) > 1"), [(6,)])
        self.bad("SELECT id FROM employees HAVING id > 1")

    def test_grouping_rule_errors(self):
        for sql in ("SELECT name, COUNT(*) FROM employees GROUP BY dept_id",
                    "SELECT dept_id, name FROM employees GROUP BY dept_id",
                    "SELECT name FROM employees WHERE id > 100 GROUP BY dept_id",
                    "SELECT id, COUNT(*) FROM employees",
                    "SELECT COUNT(*) FROM employees WHERE COUNT(*) > 1",
                    "SELECT COUNT(*) FROM employees GROUP BY COUNT(*)",
                    "SELECT SUM(COUNT(*)) FROM employees",
                    "SELECT 1 FROM employees JOIN departments d ON COUNT(*) > 1",
                    "SELECT dept_id FROM employees GROUP BY dept_id HAVING name = 'Ann'",
                    "SELECT dept_id FROM employees GROUP BY dept_id ORDER BY name",
                    "SELECT * FROM employees GROUP BY dept_id"):
            with self.subTest(sql=sql):
                self.bad(sql)

    def test_group_expression_matching(self):
        self.assertEqual(self.rows("SELECT e.dept_id, dept_id + 1, COUNT(*) FROM employees e GROUP BY dept_id"),
                         [(1, 2, 2), (2, 3, 2), (None, None, 1), (3, 4, 1)])
        self.assertEqual(self.rows("SELECT salary / 10 FROM employees GROUP BY SALARY/10"),
                         [(10.0,), (8.0,), (9.0,), (None,), (7.0,), (6.0,)])
        self.assertEqual(self.rows("SELECT dept_id * 100 + COUNT(*), 5 FROM employees GROUP BY dept_id"),
                         [(102, 5), (202, 5), (None, 5), (301, 5)])

    def test_group_by_over_a_join(self):
        self.assertEqual(self.rows("SELECT d.city, COUNT(*), SUM(e.salary) FROM employees e JOIN departments d "
                                   "ON e.dept_id = d.id GROUP BY d.city ORDER BY d.city"),
                         [("Paris", 3, 240), ("Rome", 2, 90)])

    def test_count_over_a_left_join(self):
        self.assertEqual(self.rows("SELECT d.name, COUNT(e.id) FROM departments d LEFT JOIN employees e "
                                   "ON e.dept_id = d.id GROUP BY d.name ORDER BY d.name"),
                         [("Eng", 2), ("Legal", 0), ("Ops", 2), ("Sales", 1)])
        self.assertEqual(self.rows("SELECT d.name, COUNT(*) FROM departments d LEFT JOIN employees e "
                                   "ON e.dept_id = d.id WHERE d.id = 4 GROUP BY d.name"), [("Legal", 1)])


class TestOrderingAndLimits(Base):
    def test_nulls_first_ascending_last_descending(self):
        self.assertEqual(self.ids("SELECT name FROM employees ORDER BY salary"), ["Di", "Flo", "Ed", "Bob", "Cy", "Ann"])
        self.assertEqual(self.ids("SELECT name FROM employees ORDER BY salary DESC"),
                         ["Ann", "Cy", "Bob", "Ed", "Flo", "Di"])

    def test_sort_is_stable_in_both_directions(self):
        self.assertEqual(self.ids("SELECT name FROM employees ORDER BY dept_id"), ["Ed", "Ann", "Bob", "Cy", "Di", "Flo"])
        self.assertEqual(self.ids("SELECT name FROM employees ORDER BY dept_id DESC"),
                         ["Flo", "Cy", "Di", "Ann", "Bob", "Ed"])
        self.assertEqual(self.ids("SELECT name FROM employees ORDER BY dept_id DESC, name DESC"),
                         ["Flo", "Di", "Cy", "Bob", "Ann", "Ed"])

    def test_order_by_position_alias_and_expression(self):
        self.assertEqual(self.rows("SELECT name, salary AS pay FROM employees ORDER BY 2 DESC LIMIT 2"),
                         [("Ann", 100), ("Cy", 90)])
        self.assertEqual(self.ids("SELECT name, salary AS Pay FROM employees ORDER BY pay LIMIT 2"), ["Di", "Flo"])
        self.assertEqual(self.ids("SELECT name FROM employees ORDER BY LENGTH(name), id"),
                         ["Cy", "Di", "Ed", "Ann", "Bob", "Flo"])
        self.bad("SELECT name FROM employees ORDER BY 2")
        self.bad("SELECT name FROM employees ORDER BY 0")

    def test_alias_beats_a_column_of_the_same_name(self):
        self.assertEqual(self.ids("SELECT name, 0 - id AS salary FROM employees ORDER BY salary LIMIT 2"), ["Flo", "Ed"])

    def test_order_by_aggregates(self):
        self.assertEqual(self.rows("SELECT dept_id, COUNT(*) FROM employees GROUP BY dept_id ORDER BY COUNT(*) DESC, dept_id"),
                         [(1, 2), (2, 2), (None, 1), (3, 1)])
        self.assertEqual(self.ids("SELECT dept_id FROM employees GROUP BY dept_id ORDER BY SUM(salary) DESC"),
                         [1, 2, None, 3])

    def test_order_by_mixed_types_is_an_error(self):
        self.bad("SELECT id FROM employees ORDER BY COALESCE(salary, name)")

    def test_distinct(self):
        self.assertEqual(self.ids("SELECT DISTINCT dept_id FROM employees"), [1, 2, None, 3])
        self.assertEqual(self.ids("SELECT DISTINCT city FROM departments ORDER BY city DESC"), ["Rome", "Paris", "Oslo"])
        self.assertEqual(self.ids("SELECT DISTINCT city FROM departments ORDER BY city LIMIT 2"), ["Oslo", "Paris"])
        self.assertEqual(self.rows("SELECT DISTINCT city, 1 FROM departments ORDER BY 1 LIMIT 1 OFFSET 1"), [("Paris", 1)])

    def test_limit_and_offset(self):
        self.assertEqual(self.ids("SELECT id FROM employees ORDER BY id LIMIT 2 OFFSET 3"), [4, 5])
        self.assertEqual(self.ids("SELECT id FROM employees ORDER BY id LIMIT 0"), [])
        self.assertEqual(self.ids("SELECT id FROM employees ORDER BY id LIMIT 3 OFFSET 10"), [])
        self.assertEqual(self.ids("SELECT id FROM employees LIMIT 100"), [1, 2, 3, 4, 5, 6])


if __name__ == "__main__":
    unittest.main()
