"""Rebuilding an index from the documents it holds."""
from .search import Searcher


def rebuild(searcher):
    """A fresh Searcher with the same documents, analysed with the current schema."""
    fresh = Searcher(searcher.cache.capacity)
    for doc_id in sorted(searcher.index.docs):
        fresh.add(searcher.index.docs[doc_id])
    return fresh


def verify(searcher):
    """True when the stored postings match a fresh analysis of every document."""
    other = rebuild(searcher)
    return other.index.postings == searcher.index.postings
