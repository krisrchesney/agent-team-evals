"""A process-wide memo of project summaries, keyed by project id. Task writers call `invalidate`."""

_MEMO = {}


def get(project_id):
    found = _MEMO.get(project_id)
    return None if found is None else dict(found)


def put(project_id, summary):
    _MEMO[project_id] = dict(summary)


def invalidate(project_id):
    _MEMO.pop(project_id, None)


def reset():
    _MEMO.clear()
