"""Version constraints such as ">=1.2,<2", "^1.4.0" or "~0.3"."""
import re

from .errors import ConstraintError, VersionError
from .version import Version, parse_partial

_CLAUSE = re.compile(r"^(==|!=|>=|<=|>|<|\^|~)?(.+)$")
_COMPARE = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}


def _expand(op, version, given):
    """Turn one operator and operand into plain comparisons."""
    if op in _COMPARE:
        return [(op, version)]
    parts = [version.major, version.minor, version.patch]
    if op == "^":
        # bump the leftmost non-zero part that was written (or the last written part if all are zero)
        bump = next((i for i, p in enumerate(parts[:given]) if p), given - 1)
    else:
        bump = 0 if given == 1 else 1
    upper = parts[:bump] + [parts[bump] + 1] + [0] * (2 - bump)
    # "-0" is the lowest prerelease, so the bound also excludes prereleases of the upper version
    return [(">=", version), ("<", Version("%d.%d.%d-0" % tuple(upper)))]


class Clause:
    """One comma-separated piece of a constraint."""

    def __init__(self, text):
        text = re.sub(r"\s+", "", text)
        if not text:
            raise ConstraintError("empty constraint clause")
        self.text = text
        if text == "*":
            self.op, self.operand, self._tests = "*", None, []
            return
        op, operand = _CLAUSE.match(text).groups()
        try:
            version, given = parse_partial(operand)
        except VersionError as exc:
            raise ConstraintError(f"invalid constraint {text!r}: {exc}") from None
        self.op = op or "=="
        self.operand = version
        self._tests = _expand(self.op, version, given)

    def matches(self, version):
        return all(_COMPARE[op](version, bound) for op, bound in self._tests)


class Constraint:
    """A set of clauses that must all hold."""

    def __init__(self, text):
        self.clauses = tuple(Clause(piece) for piece in text.split(","))

    def matches(self, version):
        return all(clause.matches(version) for clause in self.clauses)

    @property
    def has_prerelease_operand(self):
        return any(c.operand is not None and c.operand.is_prerelease for c in self.clauses)

    def pins(self, version):
        """True if a clause is an exact '==' (or bare) match for this version."""
        return any(c.op == "==" and c.operand == version for c in self.clauses)

    def __str__(self):
        return ",".join(c.text for c in self.clauses)

    def __repr__(self):
        return f"Constraint({str(self)!r})"
