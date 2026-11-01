"""Query grammar.

    query   := or
    or      := and ("OR" and)*
    and     := unary+            (a space between terms means AND)
    unary   := "-" primary | primary
    primary := "(" or ")" | [field ":"] (word | "quoted phrase")

A `field:` prefix must name one of KNOWN_FIELDS; anything else is a QueryError.
"""
from ..errors import QueryError
from .ast import And, Not, Or, Phrase, Term
from .lexer import lex

KNOWN_FIELDS = frozenset({"title", "body", "tags", "author"})


class _Parser:
    def __init__(self, toks):
        self.toks = toks
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def parse(self):
        if not self.toks:
            raise QueryError("empty query", field="query")
        node = self.or_()
        if self.peek() is not None:
            raise QueryError(f"unexpected {self.peek().value!r}", field="query")
        return node

    def or_(self):
        nodes = [self.and_()]
        while self.peek() is not None and self.peek().kind == "OR":
            self.take()
            nodes.append(self.and_())
        return nodes[0] if len(nodes) == 1 else Or(tuple(nodes))

    def and_(self):
        nodes = []
        while self.peek() is not None and self.peek().kind not in ("OR", "RPAREN"):
            nodes.append(self.unary())
        if not nodes:
            raise QueryError("expected a search term", field="query")
        return nodes[0] if len(nodes) == 1 else And(tuple(nodes))

    def unary(self):
        if self.peek().kind == "MINUS":
            self.take()
            if self.peek() is None:
                raise QueryError("nothing to exclude after '-'", field="query")
            return Not(self.primary())
        return self.primary()

    def primary(self):
        tok = self.take()
        if tok.kind == "LPAREN":
            node = self.or_()
            closing = self.take()
            if closing is None or closing.kind != "RPAREN":
                raise QueryError("missing ')'", field="query")
            return node
        if tok.kind not in ("WORD", "QUOTED"):
            raise QueryError(f"unexpected {tok.value!r}", field="query")
        if tok.field is not None and tok.field not in KNOWN_FIELDS:
            raise QueryError(f"unknown field {tok.field!r}", field="query")
        if tok.kind == "QUOTED":
            return Phrase(tok.value, tok.field)
        return Term(tok.value, tok.field)


def parse(text):
    if not isinstance(text, str):
        raise QueryError("query must be a string", field="query")
    return _Parser(lex(text)).parse()
