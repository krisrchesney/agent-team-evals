"""Counting documents by tag, for filter sidebars."""
from collections import Counter

from .analysis.tokenizer import words


def tag_counts(searcher, doc_ids=None):
    """tag (as written, first spelling seen) -> number of documents, most common first."""
    counts, spelling = Counter(), {}
    ids = searcher.index.doc_ids() if doc_ids is None else doc_ids
    for doc_id in ids:
        for tag in searcher.index.get(doc_id).tags:
            key = " ".join(words(tag))
            spelling.setdefault(key, tag)
            counts[key] += 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return {spelling[key]: n for key, n in ordered}


def facet_for_result(searcher, result):
    """Tag counts over every hit of a result page."""
    return tag_counts(searcher, [h.id for h in result.hits])


def narrow(searcher, doc_ids, tag):
    """Keep only documents carrying `tag` (compared as words, case-insensitively)."""
    want = " ".join(words(tag))
    return [
        d for d in doc_ids
        if want in {" ".join(words(t)) for t in searcher.index.get(d).tags}
    ]
