"""Export records in any registered format."""
from .formats import get
from .rows import prepare


def export(records, fmt, columns=None, sort_by=None, descending=False, limit=None):
    renderer = get(fmt)  # an unknown format is reported before any other problem
    names, rows = prepare(records, columns, sort_by, descending, limit)
    return renderer(names, rows)
