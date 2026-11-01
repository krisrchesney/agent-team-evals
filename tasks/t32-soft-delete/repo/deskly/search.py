"""A small inverted index over tickets: subject words count 3, body and comment words count 1."""
import re

from . import validate

_WORD = re.compile(r"[a-z0-9]+")


def tokens(text):
    return _WORD.findall(text.lower())


class SearchIndex:
    def __init__(self, store):
        self.store = store
        self._postings = {}        # word -> {ticket id: weight}

    def reindex(self, ticket_id):
        """Rebuild one ticket's postings from its current subject, body and comments."""
        self.drop(ticket_id)
        ticket = self.store.ticket(ticket_id)
        weights = {}
        for word in tokens(ticket.subject):
            weights[word] = weights.get(word, 0) + 3
        for word in tokens(ticket.body):
            weights[word] = weights.get(word, 0) + 1
        for comment in self.store.comments_of(ticket_id):
            for word in tokens(comment.text):
                weights[word] = weights.get(word, 0) + 1
        for word, weight in weights.items():
            self._postings.setdefault(word, {})[ticket_id] = weight

    def drop(self, ticket_id):
        for postings in self._postings.values():
            postings.pop(ticket_id, None)

    def query(self, text, limit=10):
        """Tickets containing every word of `text`, best score first (ties: oldest ticket first)."""
        words = tokens(text)
        if not words:
            return []
        matching = None
        for word in words:
            ids = set(self._postings.get(word, ()))
            matching = ids if matching is None else matching & ids
        scored = [(sum(self._postings[w][i] for w in words), i) for i in matching]
        scored.sort(key=lambda s: (-s[0], int(s[1][1:])))
        return [{"ticket": i, "subject": self.store.ticket(i).subject, "score": score}
                for score, i in scored[:validate.limit(limit)]]
