"""Splitting text into tokens that remember where they came from."""
import re
from dataclasses import dataclass

_WORD = re.compile(r"[^\W_]+")


@dataclass(frozen=True)
class Token:
    term: str
    position: int  # 0, 1, 2 ... among the words of the value
    start: int     # character offsets of the original word
    end: int


def tokenize(text):
    """Words are runs of letters and digits; everything else separates them. Terms are case-folded."""
    return [
        Token(m.group().casefold(), n, m.start(), m.end())
        for n, m in enumerate(_WORD.finditer(text))
    ]


def words(text):
    return [t.term for t in tokenize(text)]
