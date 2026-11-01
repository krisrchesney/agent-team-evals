"""Re-ordering a result page by something other than score."""
from .errors import QueryError

SORTS = ("score", "title", "updated")


def sort_hits(searcher, hits, by="score", descending=None):
    """Return a new list. Score sorts high to low, the others low to high, unless `descending` says."""
    if by not in SORTS:
        raise QueryError(f"cannot sort by {by!r}", field="sort")
    if by == "score":
        if descending is False:
            return sorted(hits, key=lambda h: (h.score, h.id))
        return sorted(hits, key=lambda h: (-h.score, h.id))
    def key(hit):
        doc = searcher.index.get(hit.id)
        return (getattr(doc, by).casefold(), hit.id)
    return sorted(hits, key=key, reverse=bool(descending))
