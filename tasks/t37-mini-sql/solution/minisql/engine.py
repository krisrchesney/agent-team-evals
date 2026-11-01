"""Running a Query against a Catalog. See docs/SPEC.md."""
import dataclasses
import decimal
import re
from collections import namedtuple

from .ast import Between, Binary, Column, Func, InList, IsNull, Like, Literal, Unary
from .errors import QueryError

Result = namedtuple("Result", "columns rows")  # columns: list of names; rows: list of tuples

AGGREGATES = {"COUNT", "SUM", "AVG", "MIN", "MAX"}
SCALARS = {"UPPER": (1, 1), "LOWER": (1, 1), "LENGTH": (1, 1), "ABS": (1, 1), "COALESCE": (2, None), "ROUND": (1, 2)}


def is_agg(node):
    return isinstance(node, Func) and node.name in AGGREGATES


def children(node):
    if isinstance(node, Unary):
        return [node.operand]
    if isinstance(node, Binary):
        return [node.left, node.right]
    if isinstance(node, IsNull):
        return [node.expr]
    if isinstance(node, InList):
        return [node.expr] + list(node.items)
    if isinstance(node, Like):
        return [node.expr, node.pattern]
    if isinstance(node, Between):
        return [node.expr, node.low, node.high]
    if isinstance(node, Func):
        return list(node.args)
    return []


def contains_agg(node):
    return is_agg(node) or any(contains_agg(c) for c in children(node))


class Scope:
    def __init__(self, cols):
        self.cols = cols  # list of (alias, lower-case name, header spelling)

    def resolve(self, col):
        hits = [i for i, (alias, name, _) in enumerate(self.cols) if name == col.name and col.table in (None, alias)]
        if not hits:
            if col.table is not None and not any(c[0] == col.table for c in self.cols):
                raise QueryError("unknown table: %s" % col.table)
            raise QueryError("unknown column: %s" % col.name)
        if len(hits) > 1:
            raise QueryError("ambiguous column: %s" % col.name)
        return hits[0]


def canon(node, scope):
    if isinstance(node, Column):
        return ("col", scope.resolve(node))
    if isinstance(node, (tuple, list)):
        return tuple(canon(n, scope) for n in node)
    if dataclasses.is_dataclass(node):
        return (type(node).__name__,) + tuple(canon(getattr(node, f.name), scope) for f in dataclasses.fields(node))
    return node


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def to_bool(v):
    if v is None:
        return None
    if isinstance(v, str):
        raise QueryError("a string is not a condition")
    return v != 0


def from_bool(b):
    return None if b is None else (1 if b else 0)


def compare(op, a, b):
    if a is None or b is None:
        return None
    if isinstance(a, str) != isinstance(b, str):
        raise QueryError("cannot compare a number with a string")
    res = {"=": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
    return 1 if res else 0


def and3(a, b):
    if a is False or b is False:
        return False
    if a is None or b is None:
        return None
    return True


def not3(a):
    return None if a is None else (not a)


def like_regex(pattern):
    out = []
    for ch in pattern:
        out.append(".*" if ch == "%" else "." if ch == "_" else re.escape(ch))
    return re.compile("".join(out), re.IGNORECASE | re.ASCII | re.DOTALL)


class Ev:
    def __init__(self, scope, group_canons=()):
        self.scope = scope
        self.group_canons = set(group_canons)

    def eval(self, node, row, rows=None):
        if rows is not None and self.group_canons and canon(node, self.scope) in self.group_canons:
            return self.eval(node, row)
        if isinstance(node, Literal):
            return node.value
        if isinstance(node, Column):
            return row[self.scope.resolve(node)]
        if isinstance(node, Unary):
            v = self.eval(node.operand, row, rows)
            if node.op == "NOT":
                return from_bool(not3(to_bool(v)))
            if v is None:
                return None
            if not is_num(v):
                raise QueryError("cannot negate a string")
            return -v
        if isinstance(node, Binary):
            return self.binary(node, row, rows)
        if isinstance(node, IsNull):
            res = self.eval(node.expr, row, rows) is None
            return 1 if res != node.negated else 0
        if isinstance(node, InList):
            return self.in_list(node, row, rows)
        if isinstance(node, Like):
            x, p = self.eval(node.expr, row, rows), self.eval(node.pattern, row, rows)
            if x is None or p is None:
                return None
            if not isinstance(x, str) or not isinstance(p, str):
                raise QueryError("LIKE needs strings")
            res = like_regex(p).fullmatch(x) is not None
            return 1 if res != node.negated else 0
        if isinstance(node, Between):
            x = self.eval(node.expr, row, rows)
            lo, hi = self.eval(node.low, row, rows), self.eval(node.high, row, rows)
            res = and3(to_bool(compare(">=", x, lo)), to_bool(compare("<=", x, hi)))
            return from_bool(not3(res) if node.negated else res)
        if isinstance(node, Func):
            if node.name in AGGREGATES:
                if rows is None:
                    raise QueryError("aggregate not allowed here")
                return self.aggregate(node, rows)
            return self.scalar(node, row, rows)
        raise QueryError("cannot evaluate %r" % (node,))

    def binary(self, node, row, rows):
        a, b = self.eval(node.left, row, rows), self.eval(node.right, row, rows)
        op = node.op
        if op == "AND":
            return from_bool(and3(to_bool(a), to_bool(b)))
        if op == "OR":
            x, y = to_bool(a), to_bool(b)
            if x is True or y is True:
                return 1
            return None if x is None or y is None else 0
        if op in ("=", "!=", "<", "<=", ">", ">="):
            return compare(op, a, b)
        if a is None or b is None:
            return None
        if not is_num(a) or not is_num(b):
            raise QueryError("arithmetic needs numbers")
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        return None if b == 0 else a / b

    def in_list(self, node, row, rows):
        x = self.eval(node.expr, row, rows)
        if x is None:
            return None
        saw_null, found = False, False
        for item in node.items:
            v = self.eval(item, row, rows)
            if v is None:
                saw_null = True
            elif compare("=", x, v) == 1:
                found = True
                break
        res = True if found else (None if saw_null else False)
        return from_bool(not3(res) if node.negated else res)

    def scalar(self, node, row, rows):
        vals = [self.eval(a, row, rows) for a in node.args]
        name = node.name
        if name == "COALESCE":
            return next((v for v in vals if v is not None), None)
        v = vals[0]
        if v is None:
            return None
        if name in ("UPPER", "LOWER", "LENGTH"):
            if not isinstance(v, str):
                raise QueryError("%s needs a string" % name)
            if name == "LENGTH":
                return len(v)
            return v.upper() if name == "UPPER" else v.lower()
        if not is_num(v):
            raise QueryError("%s needs a number" % name)
        if name == "ABS":
            return abs(v)
        digits = node.args[1].value if len(node.args) > 1 else 0
        quantum = decimal.Decimal(1).scaleb(-digits)
        return float(decimal.Decimal(repr(float(v))).quantize(quantum, rounding=decimal.ROUND_HALF_UP))

    def aggregate(self, node, rows):
        if node.star:
            return len(rows)
        vals = [v for v in (self.eval(node.args[0], r) for r in rows) if v is not None]
        if node.distinct:
            seen, uniq = set(), []
            for v in vals:
                if v not in seen:
                    seen.add(v)
                    uniq.append(v)
            vals = uniq
        if node.name == "COUNT":
            return len(vals)
        if not vals:
            return None
        if node.name in ("SUM", "AVG"):
            if not all(is_num(v) for v in vals):
                raise QueryError("%s needs numbers" % node.name)
            total = sum(vals)
            return total if node.name == "SUM" else total / len(vals)
        try:
            return min(vals) if node.name == "MIN" else max(vals)
        except TypeError:
            raise QueryError("cannot compare numbers with strings") from None


def check_funcs(node):
    if isinstance(node, Func):
        if node.name in AGGREGATES:
            if not node.star and len(node.args) != 1:
                raise QueryError("%s takes one argument" % node.name)
            if node.distinct and node.name not in ("COUNT", "SUM", "AVG"):
                raise QueryError("DISTINCT is not allowed in %s" % node.name)
        elif node.name in SCALARS:
            low, high = SCALARS[node.name]
            if len(node.args) < low or (high is not None and len(node.args) > high) or node.distinct:
                raise QueryError("wrong arguments for %s" % node.name)
            if node.name == "ROUND" and len(node.args) == 2:
                n = node.args[1]
                if not (isinstance(n, Literal) and type(n.value) is int and n.value >= 0):
                    raise QueryError("ROUND digits must be a non-negative integer literal")
        else:
            raise QueryError("unknown function: %s" % node.name)
    for c in children(node):
        check_funcs(c)


def check_row(node, scope):
    canon(node, scope)
    if contains_agg(node):
        raise QueryError("aggregates are not allowed here")
    check_funcs(node)


def check_group(node, scope, group_canons):
    check_funcs(node)

    def visit(n):
        if canon(n, scope) in group_canons:
            return
        if is_agg(n):
            for a in n.args:
                check_row(a, scope)
            return
        if isinstance(n, Column):
            raise QueryError("column %s must appear in GROUP BY or inside an aggregate" % n.name)
        for c in children(n):
            visit(c)

    visit(node)


def sort_key(v):
    return (0,) if v is None else (1, v)


def execute(query, catalog):
    tables, aliases = [], set()
    for ref in [query.table] + [j.table for j in query.joins]:
        table = catalog.table(ref.name)
        alias = ref.alias or ref.name
        if alias in aliases:
            raise QueryError("duplicate table alias: %s" % alias)
        aliases.add(alias)
        tables.append((alias, table))
    all_cols = [(alias, c.lower(), c) for alias, t in tables for c in t.columns]

    rows = [tuple(r) for r in tables[0][1].rows]
    width = len(tables[0][1].columns)
    for k, join in enumerate(query.joins, 1):
        right = tables[k][1]
        scope = Scope(all_cols[:width + len(right.columns)])
        check_row(join.on, scope)
        ev = Ev(scope)
        joined = []
        for left in rows:
            matched = False
            for r in right.rows:
                combined = left + tuple(r)
                if to_bool(ev.eval(join.on, combined)):
                    joined.append(combined)
                    matched = True
            if not matched and join.kind == "LEFT":
                joined.append(left + (None,) * len(right.columns))
        rows = joined
        width += len(right.columns)

    scope = Scope(all_cols)
    if query.where is not None:
        check_row(query.where, scope)
        ev = Ev(scope)
        rows = [r for r in rows if to_bool(ev.eval(query.where, r))]

    items = []  # (expr, output name)
    for item in query.items:
        if item.star:
            cols = [c for c in all_cols if item.star_table in (None, c[0])]
            if not cols:
                raise QueryError("unknown table: %s" % item.star_table)
            items.extend((Column(alias, name), shown) for alias, name, shown in cols)
        elif item.alias is not None:
            items.append((item.expr, item.alias))
        elif isinstance(item.expr, Column):
            items.append((item.expr, all_cols[scope.resolve(item.expr)][2]))
        else:
            items.append((item.expr, item.text))

    alias_pos = {}
    pos = 0
    for item in query.items:
        if item.star:
            pos += len([c for c in all_cols if item.star_table in (None, c[0])])
        else:
            if item.alias is not None:
                alias_pos.setdefault(item.alias.lower(), pos)
            pos += 1

    terms = []  # ("out", index) or ("expr", node)
    for o in query.order_by:
        e = o.expr
        if isinstance(e, Literal) and type(e.value) is int:
            if not 1 <= e.value <= len(items):
                raise QueryError("ORDER BY position %d is out of range" % e.value)
            terms.append(("out", e.value - 1))
        elif isinstance(e, Column) and e.table is None and e.name in alias_pos:
            terms.append(("out", alias_pos[e.name]))
        else:
            terms.append(("expr", e))

    exprs = [e for e, _ in items] + [n for kind, n in terms if kind == "expr"]
    if query.having is not None:
        exprs.append(query.having)
    is_agg_query = bool(query.group_by) or any(contains_agg(e) for e in exprs)
    if query.having is not None and not is_agg_query:
        raise QueryError("HAVING needs GROUP BY or an aggregate")

    if is_agg_query:
        for g in query.group_by:
            check_row(g, scope)
        group_canons = {canon(g, scope) for g in query.group_by}
        for e in exprs:
            check_group(e, scope, group_canons)
        ev = Ev(scope, group_canons)
        if query.group_by:
            groups = {}
            for r in rows:
                groups.setdefault(tuple(ev.eval(g, r) for g in query.group_by), []).append(r)
            group_rows = list(groups.values())
        else:
            group_rows = [rows]
        units = [(g[0] if g else None, g) for g in group_rows]
        if query.having is not None:
            units = [(r, g) for r, g in units if to_bool(ev.eval(query.having, r, g))]
    else:
        for e in exprs:
            check_row(e, scope)
        ev = Ev(scope)
        units = [(r, None) for r in rows]

    produced = []
    for r, g in units:
        out = tuple(ev.eval(e, r, g) for e, _ in items)
        keys = [out[v] if kind == "out" else ev.eval(v, r, g) for kind, v in terms]
        produced.append((out, keys))
    for t in reversed(range(len(terms))):
        try:
            produced.sort(key=lambda p: sort_key(p[1][t]), reverse=query.order_by[t].desc)
        except TypeError:
            raise QueryError("cannot order a number against a string") from None
    result = [p[0] for p in produced]
    if query.distinct:
        seen, uniq = set(), []
        for r in result:
            if r not in seen:
                seen.add(r)
                uniq.append(r)
        result = uniq
    start = query.offset or 0
    result = result[start:]
    if query.limit is not None:
        result = result[:query.limit]
    return Result([name for _, name in items], result)
