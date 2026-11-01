"""A process-wide cache of task views, keyed by tenant and task id. Writers drop the key; `reset` empties it."""

_VIEWS = {}


def get(tenant, key):
    view = _VIEWS.get((tenant, key))
    return None if view is None else {**view, "labels": list(view["labels"])}


def put(tenant, key, view):
    _VIEWS[(tenant, key)] = {**view, "labels": list(view["labels"])}


def drop(tenant, key):
    _VIEWS.pop((tenant, key), None)


def drop_tenant(tenant):
    for key in [k for k in _VIEWS if k[0] == tenant]:
        del _VIEWS[key]


def reset():
    _VIEWS.clear()
