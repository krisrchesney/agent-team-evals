"""A process-wide inverted index over tasks, one per tenant: title words count 2, comment words count 1."""
import re

from . import validate

_WORD = re.compile(r"[a-z0-9]+")

_POSTINGS = {}        # tenant -> {word -> {task id: weight}}


def tokens(text):
    return _WORD.findall(text.lower())


def index_task(svc, task_id):
    """Rebuild one task's postings from its current title and comments."""
    drop(svc.tenant, task_id)
    task = svc.store.task(task_id)
    weights = {}
    for word in tokens(task.title):
        weights[word] = weights.get(word, 0) + 2
    for comment in svc.store.comments_of(task_id):
        for word in tokens(comment.text):
            weights[word] = weights.get(word, 0) + 1
    index = _POSTINGS.setdefault(svc.tenant, {})
    for word, weight in weights.items():
        index.setdefault(word, {})[task_id] = weight


def drop(tenant, task_id):
    for postings in _POSTINGS.get(tenant, {}).values():
        postings.pop(task_id, None)


def drop_tenant(tenant):
    _POSTINGS.pop(tenant, None)


def query(svc, text, limit=None):
    """Tasks containing every word of `text`, best score first (ties: oldest task first)."""
    limit = validate.limit(limit, default=10)
    words = tokens(text)
    if not words:
        return []
    index = _POSTINGS.get(svc.tenant, {})
    matching = None
    for word in words:
        ids = set(index.get(word, ()))
        matching = ids if matching is None else matching & ids
    scored = [(sum(index[w][i] for w in words), i) for i in matching]
    scored.sort(key=lambda s: (-s[0], int(s[1][1:])))
    return [{"task": i, "title": svc.store.task(i).title, "score": score} for score, i in scored[:limit]]


def reset():
    _POSTINGS.clear()
