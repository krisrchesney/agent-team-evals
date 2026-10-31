"""Running queries against an index, with result caching."""
import math
from dataclasses import dataclass, field

from . import cache as cache_mod
from . import schema
from .analysis import analyze
from .errors import QueryError
from .highlight import highlight_doc
from .index import Index
from .query import And, Not, Or, Phrase, Term, canon, parse


@dataclass
class Hit:
    id: str
    score: float
    highlights: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    query: str
    total: int
    hits: list


class Searcher:
    def __init__(self, cache_size=128):
        self.index = Index()
        self.cache = cache_mod.ResultCache(cache_size)

    # -- changing the index -------------------------------------------------

    def add(self, doc):
        self.index.add(doc)

    def update(self, doc):
        self.index.update(doc)

    def remove(self, doc_id):
        self.index.remove(doc_id)

    # -- searching ----------------------------------------------------------

    def search(self, text, fields=None, limit=10, offset=0, highlight=False):
        """Ranked hits for `text`. `fields` limits where plain (un-prefixed) terms look; None = all."""
        node = parse(text)
        searched = self._check_fields(fields)
        if not isinstance(limit, int) or limit < 1 or not isinstance(offset, int) or offset < 0:
            raise QueryError("limit must be at least 1 and offset at least 0", field="limit")
        key = cache_mod.make_key(canon(node), fields, limit, offset, highlight, self.index.generation)
        found = self.cache.get(key)
        if found is not None:
            return found
        scores = self._eval(node, searched)
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        page = ranked[offset:offset + limit]
        hits = []
        for doc_id, score in page:
            marks = highlight_doc(self.index.get(doc_id), node, searched) if highlight else {}
            hits.append(Hit(doc_id, round(score, 6), marks))
        result = SearchResult(text, len(ranked), hits)
        self.cache.put(key, result)
        return result

    def _check_fields(self, fields):
        if fields is None:
            return list(schema.default_fields())
        if not isinstance(fields, (list, tuple)) or not fields:
            raise QueryError("fields must be a non-empty list", field="fields")
        for name in fields:
            if name not in schema.FIELDS:
                raise QueryError(f"unknown field {name!r}", field="fields")
        return list(fields)

    # -- evaluation ---------------------------------------------------------

    def _eval(self, node, fields):
        if isinstance(node, (Term, Phrase)):
            return self._match(node, fields)
        if isinstance(node, Not):
            everyone = {d: 0.0 for d in self.index.doc_ids()}
            for d in self._eval(node.node, fields):
                everyone.pop(d, None)
            return everyone
        if isinstance(node, Or):
            out = {}
            for child in node.nodes:
                for d, s in self._eval(child, fields).items():
                    out[d] = out.get(d, 0.0) + s
            return out
        if isinstance(node, And):
            positive = [c for c in node.nodes if not isinstance(c, Not)]
            negative = [c for c in node.nodes if isinstance(c, Not)]
            if positive:
                parts = [self._eval(c, fields) for c in positive]
                keep = set(parts[0]).intersection(*parts[1:])
                out = {d: sum(p[d] for p in parts) for d in keep}
            else:
                out = {d: 0.0 for d in self.index.doc_ids()}
            for neg in negative:
                for d in self._eval(neg.node, fields):
                    out.pop(d, None)
            return out
        raise TypeError(node)

    def _match(self, node, fields):
        names = [node.field] if node.field else fields
        out = {}
        for name in names:
            spec = schema.get(name)
            tokens = analyze(spec.analyzer, node.text)
            for doc_id, count in self._phrase(name, [t.term for t in tokens]).items():
                out[doc_id] = out.get(doc_id, 0.0) + spec.boost * (1 + math.log(count))
        return out

    def _phrase(self, name, terms):
        """doc id -> number of places where `terms` occur next to each other in field `name`."""
        if not terms:
            return {}
        postings = [self.index.lookup(name, t) for t in terms]
        docs = set(postings[0]).intersection(*postings[1:])
        out = {}
        for doc_id in docs:
            starts = set(postings[0][doc_id])
            for step, posting in enumerate(postings[1:], start=1):
                starts = {p for p in starts if p + step in set(posting[doc_id])}
            if starts:
                out[doc_id] = len(starts)
        return out
