"""A small integer expression evaluator."""
import re


class EvalError(Exception):
    pass


class ParseError(EvalError):
    pass


def evaluate(text):
    """Evaluate +, -, *, / and parentheses on integers."""
    tokens = re.findall(r"\d+|[-+*/()]", text)
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def take():
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def atom():
        tok = take()
        if tok == "(":
            value = expr()
            take()
            return value
        return int(tok)

    def term():
        value = atom()
        while peek() in ("*", "/"):
            op = take()
            rhs = atom()
            value = value * rhs if op == "*" else value // rhs
        return value

    def expr():
        value = term()
        while peek() in ("+", "-"):
            op = take()
            rhs = term()
            value = value + rhs if op == "+" else value - rhs
        return value

    return expr()
