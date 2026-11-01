"""A process-wide memo of project summaries, keyed by tenant and project id. Task writers call `invalidate`."""

_MEMO = {}


def get(tenant, project_id):
    found = _MEMO.get((tenant, project_id))
    return None if found is None else dict(found)


def put(tenant, project_id, summary):
    _MEMO[(tenant, project_id)] = dict(summary)


def invalidate(tenant, project_id):
    _MEMO.pop((tenant, project_id), None)


def drop_tenant(tenant):
    for key in [k for k in _MEMO if k[0] == tenant]:
        del _MEMO[key]


def reset():
    _MEMO.clear()
