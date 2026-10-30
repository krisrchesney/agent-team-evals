"""Version constraints such as ">=1.2,<2"."""
import re

from .errors import ConstraintError, VersionError
from .version import Version

_CLAUSE = re.compile(r"^(==|>=|<=|>|<)?(.+)$")
_COMPARE = {
    "==": lambda a, b: a == b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}


class Clause:
    """One comma-separated piece of a constraint."""

    def __init__(self, text):
        text = text.strip()
        if not text:
            raise ConstraintError("empty constraint clause")
        self.text = text
        if text == "*":
            self.op, self.operand = "*", None
            return
        op, operand = _CLAUSE.match(text.replace(" ", "")).groups()
        try:
            self.operand = Version(operand)
        except VersionError as exc:
            raise ConstraintError(f"invalid constraint {text!r}: {exc}") from None
        self.op = op or "=="

    def matches(self, version):
        if self.op == "*":
            return True
        return _COMPARE[self.op](version, self.operand)


class Constraint:
    """A set of clauses that must all hold."""

    def __init__(self, text):
        self.text = text
        self.clauses = tuple(Clause(piece) for piece in text.split(","))

    def matches(self, version):
        return all(clause.matches(version) for clause in self.clauses)

    def __str__(self):
        return self.text

    def __repr__(self):
        return f"Constraint({self.text!r})"
