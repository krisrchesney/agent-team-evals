"""A process-wide cache of task views, keyed by task id. Writers drop the key; `reset` empties it."""

_VIEWS = {}


def get(key):
    view = _VIEWS.get(key)
    return None if view is None else {**view, "labels": list(view["labels"])}


def put(key, view):
    _VIEWS[key] = {**view, "labels": list(view["labels"])}


def drop(key):
    _VIEWS.pop(key, None)


def reset():
    _VIEWS.clear()
