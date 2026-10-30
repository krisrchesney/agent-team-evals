"""A small integer expression language: parser plus evaluator."""
import re


class EvalError(Exception):
    pass


class ParseError(EvalError):
    pass


_TOKEN = re.compile(r"\s*(?:(\d+)|([A-Za-z_]\w*)|(\*\*|<=|>=|==|!=|&&|\|\||[-+*/%<>!(),?:]))")
_CMP = ("<", "<=", ">", ">=", "==", "!=")


def _tokenize(text):
    tokens, pos = [], 0
    while True:
        if text[pos:].strip() == "":
            return tokens
        m = _TOKEN.match(text, pos)
        if not m:
            raise ParseError(f"unexpected character at {pos}")
        num, name, op = m.groups()
        tokens.append(("num", int(num)) if num is not None else ("name", name) if name else ("op", op))
        pos = m.end()


class _Parser:
    """Recursive descent that builds a tuple AST; nothing is evaluated while parsing."""

    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0

    def peek_op(self):
        tok = self.toks[self.i] if self.i < len(self.toks) else None
        return tok[1] if tok and tok[0] == "op" else None

    def take(self, *ops):
        if self.peek_op() in ops:
            self.i += 1
            return self.toks[self.i - 1][1]
        return None

    def expect(self, op):
        if self.take(op) is None:
            raise ParseError(f"expected {op!r}")

    def parse(self):
        node = self.ternary()
        if self.i != len(self.toks):
            raise ParseError("unexpected trailing input")
        return node

    def ternary(self):
        cond = self.logical_or()
        if self.take("?"):
            then = self.ternary()
            self.expect(":")
            return ("?", cond, then, self.ternary())
        return cond

    def logical_or(self):
        node = self.logical_and()
        while self.take("||"):
            node = ("||", node, self.logical_and())
        return node

    def logical_and(self):
        node = self.comparison()
        while self.take("&&"):
            node = ("&&", node, self.comparison())
        return node

    def comparison(self):
        node = self.additive()
        while (op := self.take(*_CMP)) is not None:
            node = (op, node, self.additive())
        return node

    def additive(self):
        node = self.term()
        while (op := self.take("+", "-")) is not None:
            node = (op, node, self.term())
        return node

    def term(self):
        node = self.unary()
        while (op := self.take("*", "/", "%")) is not None:
            node = (op, node, self.unary())
        return node

    def unary(self):
        op = self.take("-", "+", "!")
        if op is not None:
            return ("u" + op, self.unary())
        return self.power()

    def power(self):
        base = self.atom()
        if self.take("**"):
            return ("**", base, self.unary())  # exponent may be unary; recursion makes ** right-associative
        return base

    def atom(self):
        if self.i >= len(self.toks):
            raise ParseError("unexpected end of input")
        kind, value = self.toks[self.i]
        self.i += 1
        if kind == "num":
            return ("num", value)
        if kind == "name":
            if self.take("("):
                args = []
                if not self.take(")"):
                    args.append(self.ternary())
                    while self.take(","):
                        args.append(self.ternary())
                    self.expect(")")
                return ("call", value, args)
            return ("var", value)
        if value == "(":
            node = self.ternary()
            self.expect(")")
            return node
        raise ParseError(f"unexpected {value!r}")


def _trunc_div(a, b):
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


_FUNCS = {"min": (1, None, min), "max": (1, None, max), "abs": (1, 1, lambda xs: abs(xs[0]))}


def _eval(node, env):
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "var":
        if node[1] not in env:
            raise EvalError(f"undefined variable {node[1]!r}")
        return env[node[1]]
    if kind == "call":
        spec = _FUNCS.get(node[1])
        if spec is None:
            raise EvalError(f"unknown function {node[1]!r}")
        lo, hi, fn = spec
        if len(node[2]) < lo or (hi is not None and len(node[2]) > hi):
            raise EvalError(f"wrong number of arguments to {node[1]}")
        return fn([_eval(arg, env) for arg in node[2]])
    if kind == "?":
        return _eval(node[2] if _eval(node[1], env) else node[3], env)
    if kind == "u-":
        return -_eval(node[1], env)
    if kind == "u+":
        return _eval(node[1], env)
    if kind == "u!":
        return int(not _eval(node[1], env))
    if kind == "&&":
        return int(bool(_eval(node[1], env)) and bool(_eval(node[2], env)))
    if kind == "||":
        return int(bool(_eval(node[1], env)) or bool(_eval(node[2], env)))
    a, b = _eval(node[1], env), _eval(node[2], env)
    if kind == "+":
        return a + b
    if kind == "-":
        return a - b
    if kind == "*":
        return a * b
    if kind in ("/", "%"):
        if b == 0:
            raise EvalError("division by zero")
        q = _trunc_div(a, b)
        return q if kind == "/" else a - b * q
    if kind == "**":
        if b < 0:
            raise EvalError("negative exponent")
        return a ** b
    return int({"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "==": a == b, "!=": a != b}[kind])


def evaluate(text, variables=None):
    """Evaluate an integer expression and return an int."""
    tree = _Parser(_tokenize(text)).parse()
    return _eval(tree, dict(variables or {}))
