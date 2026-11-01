"""Why did this document score what it did?"""
import math

from . import schema
from .analysis import analyze
from .query import And, Or, Phrase, Term, walk


def explain(searcher, text_node, doc_id, fields=None):
    """A list of (field, term, count, contribution) for every term of the query found in the document."""
    fields = list(fields or schema.default_fields())
    rows = []
    for part in walk(text_node):
        if not isinstance(part, (Term, Phrase)):
            continue
        for name in ([part.field] if part.field else fields):
            spec = schema.get(name)
            for tok in analyze(spec.analyzer, part.text):
                positions = searcher.index.lookup(name, tok.term).get(doc_id)
                if positions:
                    count = len(positions)
                    rows.append((name, tok.term, count, round(spec.boost * (1 + math.log(count)), 6)))
    return rows


def total(rows):
    return round(sum(r[3] for r in rows), 6)


def describe(rows):
    if not rows:
        return "no matching terms"
    return "; ".join(f"{t!r} in {f} x{c} = {s}" for f, t, c, s in rows)


def is_boolean(node):
    return isinstance(node, (And, Or))
