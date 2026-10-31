"""A Library bundles a searcher with settings, a query log and synonyms."""
from . import config, serializer
from .errors import QueryError
from .querylog import QueryLog
from .search import Searcher
from .suggest import suggest_query
from .synonyms import SynonymTable


class Library:
    def __init__(self, settings=None):
        self.settings = config.load(settings)
        self.searcher = Searcher(self.settings.cache_size)
        self.log = QueryLog()
        self.synonyms = SynonymTable()

    def add(self, data):
        """Add a document given as a dict (see serializer.from_dict)."""
        doc = serializer.from_dict(data)
        self.searcher.add(doc)
        return doc

    def replace(self, data):
        doc = serializer.from_dict(data)
        self.searcher.update(doc)
        return doc

    def remove(self, doc_id):
        self.searcher.remove(doc_id)

    def search(self, text, fields=None, limit=None, offset=0, highlight=False, expand=False):
        limit = self.settings.default_limit if limit is None else limit
        if limit > self.settings.max_limit:
            raise QueryError(f"limit cannot exceed {self.settings.max_limit}", field="limit")
        if expand:
            text = self.synonyms.expand_query(text)
        result = self.searcher.search(text, fields=fields, limit=limit, offset=offset, highlight=highlight)
        if self.settings.log_queries:
            self.log.record(text, result.total)
        return result

    def did_you_mean(self, text):
        if not self.settings.suggest:
            return None
        return suggest_query(self.searcher.index, text)

    def stats(self):
        return {"index": self.searcher.index.stats(), "cache": self.searcher.cache.stats(),
                "queries": len(self.log.entries)}
