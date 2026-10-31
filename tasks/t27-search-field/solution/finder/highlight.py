"""Wrapping the matched words of a document in <em> tags."""
from . import schema
from .analysis import analyze
from .documents import field_values
from .query import Not, Phrase, Term, walk

HIGHLIGHT_FIELDS = ("title", "body", "tags", "author")


def query_terms(node, fields):
    """field -> set of analysed terms the query asks for (negated parts are left out)."""
    wanted = {name: set() for name in fields}
    skip = set()
    for part in walk(node):
        if isinstance(part, Not):
            skip.update(id(n) for n in walk(part.node))
    for part in walk(node):
        if id(part) in skip or not isinstance(part, (Term, Phrase)):
            continue
        targets = [part.field] if part.field else fields
        for name in targets:
            if name not in wanted:
                wanted[name] = set()
            for tok in analyze(schema.get(name).analyzer, part.text):
                wanted[name].add(tok.term)
    return wanted


def mark(text, analyzer, terms):
    """`text` with every word whose analysed form is in `terms` wrapped in <em>...</em>."""
    out, last = [], 0
    for tok in analyze(analyzer, text):
        if tok.term in terms:
            out.append(text[last:tok.start])
            out.append("<em>" + text[tok.start:tok.end] + "</em>")
            last = tok.end
    out.append(text[last:])
    return "".join(out)


def highlight_doc(doc, node, fields):
    """field -> highlighted text, for the highlightable fields where something matched."""
    wanted = query_terms(node, fields)
    values = field_values(doc)
    result = {}
    for name in HIGHLIGHT_FIELDS:
        terms = wanted.get(name)
        if not terms:
            continue
        spec = schema.get(name)
        pieces = [mark(v, spec.analyzer, terms) for v in values[name]]
        if any("<em>" in p for p in pieces):
            result[name] = " | ".join(pieces)
    return result
