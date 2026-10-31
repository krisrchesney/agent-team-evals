"""Splitting a query string into tokens."""
from dataclasses import dataclass

from ..errors import QueryError


@dataclass(frozen=True)
class Tok:
    kind: str   # WORD, QUOTED, MINUS, LPAREN, RPAREN, OR
    value: str
    field: str = None


def lex(text):
    toks = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch == "(":
            toks.append(Tok("LPAREN", ch))
            i += 1
        elif ch == ")":
            toks.append(Tok("RPAREN", ch))
            i += 1
        elif ch == "-" and (not toks or toks[-1].kind in ("LPAREN", "OR") or text[i - 1].isspace()):
            toks.append(Tok("MINUS", ch))
            i += 1
        else:
            field, i = _field_prefix(text, i)
            if i < n and text[i] == '"':
                end = text.find('"', i + 1)
                if end < 0:
                    raise QueryError("unterminated quote", field="query")
                toks.append(Tok("QUOTED", text[i + 1:end], field))
                i = end + 1
            else:
                j = i
                while j < n and not text[j].isspace() and text[j] not in '()"':
                    j += 1
                word = text[i:j]
                if not word:
                    raise QueryError(f"unexpected {text[i]!r}", field="query")
                if field is None and word == "OR":
                    toks.append(Tok("OR", word))
                else:
                    toks.append(Tok("WORD", word, field))
                i = j
    return toks


def _field_prefix(text, i):
    """If a word starts with `name:`, return (name, index after the colon)."""
    j = i
    while j < len(text) and (text[j].isalnum() or text[j] == "_"):
        j += 1
    if j > i and j < len(text) and text[j] == ":":
        return text[i:j], j + 1
    return None, i
