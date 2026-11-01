"""SQL text to a Query tree. See docs/SPEC.md."""
import re

from .ast import (Between, Binary, Column, Func, InList, IsNull, Join, Like, Literal, OrderItem, Query, SelectItem,
                  TableRef, Unary)
from .errors import ParseError

KEYWORDS = {"SELECT", "DISTINCT", "FROM", "WHERE", "GROUP", "BY", "HAVING", "ORDER", "ASC", "DESC", "LIMIT",
            "OFFSET", "JOIN", "INNER", "LEFT", "OUTER", "ON", "AS", "AND", "OR", "NOT", "IS", "NULL", "IN", "LIKE",
            "BETWEEN", "TRUE", "FALSE"}
COMPARE = {"=": "=", "!=": "!=", "<>": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}

TOKEN_RE = re.compile(r"""
    (?P<ws>\s+|--[^\n]*)
  | (?P<num>[0-9]+(?:\.[0-9]+)?)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op><=|>=|<>|!=|[=<>+\-*/(),.;])
""", re.X)


class Tok:
    def __init__(self, kind, value, pos, end):
        self.kind, self.value, self.pos, self.end = kind, value, pos, end


def tokenize(sql):
    toks, i = [], 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'":
            j, buf = i + 1, []
            while True:
                if j >= len(sql):
                    raise ParseError("unterminated string", i)
                if sql[j] == "'":
                    if sql[j + 1:j + 2] == "'":
                        buf.append("'")
                        j += 2
                        continue
                    break
                buf.append(sql[j])
                j += 1
            toks.append(Tok("str", "".join(buf), i, j + 1))
            i = j + 1
            continue
        m = TOKEN_RE.match(sql, i)
        if not m:
            raise ParseError("unexpected character %r" % ch, i)
        kind, text = m.lastgroup, m.group()
        if kind == "ident":
            up = text.upper()
            toks.append(Tok("kw", up, i, m.end()) if up in KEYWORDS else Tok("ident", text.lower(), i, m.end()))
        elif kind in ("num", "op"):
            toks.append(Tok(kind, text, i, m.end()))
        i = m.end()
    toks.append(Tok("eof", "", len(sql), len(sql)))
    return toks


class Parser:
    def __init__(self, sql):
        self.sql = sql
        self.toks = tokenize(sql)
        self.i = 0
        self.last_end = 0

    # -- token helpers ---------------------------------------------------------------------------

    def peek(self, k=0):
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def next(self):
        t = self.toks[self.i]
        if t.kind != "eof":
            self.i += 1
        self.last_end = t.end
        return t

    def is_kw(self, *words, k=0):
        t = self.peek(k)
        return t.kind == "kw" and t.value in words

    def is_op(self, *ops, k=0):
        t = self.peek(k)
        return t.kind == "op" and t.value in ops

    def accept_kw(self, *words):
        if self.is_kw(*words):
            return self.next()
        return None

    def accept_op(self, *ops):
        if self.is_op(*ops):
            return self.next()
        return None

    def fail(self, what):
        t = self.peek()
        raise ParseError("expected %s" % what, t.pos)

    def expect_kw(self, word):
        if not self.is_kw(word):
            self.fail(word)
        return self.next()

    def expect_op(self, op):
        if not self.is_op(op):
            self.fail("'%s'" % op)
        return self.next()

    def ident(self):
        if self.peek().kind != "ident":
            self.fail("a name")
        return self.next().value

    # -- statement -------------------------------------------------------------------------------

    def statement(self):
        self.expect_kw("SELECT")
        distinct = bool(self.accept_kw("DISTINCT"))
        items = [self.select_item()]
        while self.accept_op(","):
            items.append(self.select_item())
        self.expect_kw("FROM")
        table = self.table_ref()
        joins = []
        while True:
            if self.accept_kw("JOIN"):
                kind = "INNER"
            elif self.is_kw("INNER") and self.is_kw("JOIN", k=1):
                self.next()
                self.next()
                kind = "INNER"
            elif self.is_kw("LEFT"):
                self.next()
                self.accept_kw("OUTER")
                self.expect_kw("JOIN")
                kind = "LEFT"
            else:
                break
            ref = self.table_ref()
            self.expect_kw("ON")
            joins.append(Join(kind, ref, self.expr()))
        where = self.expr() if self.accept_kw("WHERE") else None
        group_by = []
        if self.accept_kw("GROUP"):
            self.expect_kw("BY")
            group_by.append(self.expr())
            while self.accept_op(","):
                group_by.append(self.expr())
        having = self.expr() if self.accept_kw("HAVING") else None
        order_by = []
        if self.accept_kw("ORDER"):
            self.expect_kw("BY")
            while True:
                e = self.expr()
                desc = False
                if self.accept_kw("DESC"):
                    desc = True
                else:
                    self.accept_kw("ASC")
                order_by.append(OrderItem(e, desc))
                if not self.accept_op(","):
                    break
        limit = offset = None
        if self.accept_kw("LIMIT"):
            limit = self.count()
            if self.accept_kw("OFFSET"):
                offset = self.count()
        self.accept_op(";")
        if self.peek().kind != "eof":
            raise ParseError("unexpected text after the statement", self.peek().pos)
        return Query(distinct, tuple(items), table, tuple(joins), where, tuple(group_by), having, tuple(order_by),
                     limit, offset)

    def count(self):
        t = self.peek()
        if t.kind != "num" or "." in t.value:
            self.fail("a non-negative integer")
        self.next()
        return int(t.value)

    def table_ref(self):
        name = self.ident()
        alias = None
        if self.accept_kw("AS"):
            alias = self.ident()
        elif self.peek().kind == "ident":
            alias = self.ident()
        return TableRef(name, alias)

    def select_item(self):
        if self.is_op("*"):
            self.next()
            return SelectItem(None, None, "*", star=True)
        if self.peek().kind == "ident" and self.is_op(".", k=1) and self.is_op("*", k=2):
            start = self.peek().pos
            table = self.next().value
            self.next()
            self.next()
            return SelectItem(None, None, self.sql[start:self.last_end], star=True, star_table=table)
        start = self.peek().pos
        e = self.expr()
        text = self.sql[start:self.last_end]
        alias = None
        if self.accept_kw("AS"):
            t = self.peek()
            if t.kind != "ident":
                self.fail("an alias")
            alias = self.sql[t.pos:t.end]
            self.next()
        return SelectItem(e, alias, text)

    # -- expressions -----------------------------------------------------------------------------

    def expr(self):
        left = self.and_expr()
        while self.accept_kw("OR"):
            left = Binary("OR", left, self.and_expr())
        return left

    def and_expr(self):
        left = self.not_expr()
        while self.accept_kw("AND"):
            left = Binary("AND", left, self.not_expr())
        return left

    def not_expr(self):
        if self.accept_kw("NOT"):
            return Unary("NOT", self.not_expr())
        return self.predicate()

    def at_predicate(self):
        if self.is_op(*COMPARE):
            return True
        if self.is_kw("IS", "IN", "LIKE", "BETWEEN"):
            return True
        return self.is_kw("NOT") and self.is_kw("IN", "LIKE", "BETWEEN", k=1)

    def predicate(self):
        left = self.additive()
        if not self.at_predicate():
            return left
        if self.is_op(*COMPARE):
            op = COMPARE[self.next().value]
            node = Binary(op, left, self.additive())
        elif self.accept_kw("IS"):
            negated = bool(self.accept_kw("NOT"))
            self.expect_kw("NULL")
            node = IsNull(left, negated)
        else:
            negated = bool(self.accept_kw("NOT"))
            if self.accept_kw("IN"):
                self.expect_op("(")
                items = [self.expr()]
                while self.accept_op(","):
                    items.append(self.expr())
                self.expect_op(")")
                node = InList(left, tuple(items), negated)
            elif self.accept_kw("LIKE"):
                node = Like(left, self.additive(), negated)
            else:
                self.expect_kw("BETWEEN")
                low = self.additive()
                self.expect_kw("AND")
                node = Between(left, low, self.additive(), negated)
        if self.at_predicate():
            raise ParseError("comparisons cannot be chained", self.peek().pos)
        return node

    def additive(self):
        left = self.multiplicative()
        while self.is_op("+", "-"):
            op = self.next().value
            left = Binary(op, left, self.multiplicative())
        return left

    def multiplicative(self):
        left = self.unary()
        while self.is_op("*", "/"):
            op = self.next().value
            left = Binary(op, left, self.unary())
        return left

    def unary(self):
        if self.accept_op("-"):
            if self.peek().kind == "num":
                return Literal(-self.number(self.next().value))
            return Unary("-", self.unary())
        return self.primary()

    @staticmethod
    def number(text):
        return float(text) if "." in text else int(text)

    def primary(self):
        t = self.peek()
        if t.kind == "num":
            self.next()
            return Literal(self.number(t.value))
        if t.kind == "str":
            self.next()
            return Literal(t.value)
        if t.kind == "kw" and t.value in ("NULL", "TRUE", "FALSE"):
            self.next()
            return Literal({"NULL": None, "TRUE": 1, "FALSE": 0}[t.value])
        if self.accept_op("("):
            e = self.expr()
            self.expect_op(")")
            return e
        if t.kind == "ident":
            self.next()
            if self.accept_op("("):
                return self.call(t.value.upper())
            if self.accept_op("."):
                return Column(t.value, self.ident())
            return Column(None, t.value)
        self.fail("an expression")

    def call(self, name):
        if self.is_op("*"):
            if name != "COUNT":
                self.fail("an argument")
            self.next()
            self.expect_op(")")
            return Func(name, (), False, True)
        distinct = bool(self.accept_kw("DISTINCT"))
        args = []
        if not self.is_op(")"):
            args.append(self.expr())
            while self.accept_op(","):
                args.append(self.expr())
        self.expect_op(")")
        return Func(name, tuple(args), distinct)


def parse(sql):
    return Parser(sql).statement()
