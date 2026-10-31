"""The inverted index: field -> term -> doc id -> positions."""
from . import schema
from .analysis import analyze_values
from .documents import field_values
from .errors import Conflict, NotFound


class Index:
    def __init__(self):
        self.docs = {}
        self.postings = {name: {} for name in schema.field_names()}
        self.lengths = {name: {} for name in schema.field_names()}
        self._terms = {}
        self.generation = 0

    def __len__(self):
        return len(self.docs)

    def __contains__(self, doc_id):
        return doc_id in self.docs

    def get(self, doc_id):
        try:
            return self.docs[doc_id]
        except KeyError:
            raise NotFound(f"no document {doc_id!r}", field="id") from None

    def add(self, doc):
        if doc.id in self.docs:
            raise Conflict(f"document {doc.id!r} is already indexed", field="id")
        self._index(doc)

    def update(self, doc):
        self.get(doc.id)
        self._unindex(doc.id)
        self._index(doc)

    def remove(self, doc_id):
        self.get(doc_id)
        self._unindex(doc_id)

    def _index(self, doc):
        seen = set()
        for name, values in field_values(doc).items():
            spec = schema.get(name)
            tokens = analyze_values(spec.analyzer, values)
            self.lengths[name][doc.id] = len(tokens)
            for tok in tokens:
                self.postings[name].setdefault(tok.term, {}).setdefault(doc.id, []).append(tok.position)
                seen.add((name, tok.term))
        self.docs[doc.id] = doc
        self._terms[doc.id] = seen
        self.generation += 1

    def _unindex(self, doc_id):
        for name, term in self._terms.pop(doc_id, ()):
            posting = self.postings[name].get(term)
            if posting is not None:
                posting.pop(doc_id, None)
                if not posting:
                    del self.postings[name][term]
        for name in self.lengths:
            self.lengths[name].pop(doc_id, None)
        del self.docs[doc_id]
        self.generation += 1

    def lookup(self, name, term):
        """doc id -> positions for one term of one field."""
        return self.postings[name].get(term, {})

    def vocabulary(self, name):
        return sorted(self.postings[name])

    def doc_ids(self):
        return list(self.docs)

    def stats(self):
        return {
            "documents": len(self.docs),
            "generation": self.generation,
            "fields": {
                name: {"terms": len(self.postings[name]), "tokens": sum(self.lengths[name].values())}
                for name in self.postings
            },
        }
