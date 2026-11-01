"""Saving and loading a whole index as one JSON document."""
import json

from . import schema, serializer
from .errors import FinderError
from .search import Searcher

FORMAT = 2


class SnapshotError(FinderError):
    """The snapshot cannot be loaded."""


def dump(searcher):
    index = searcher.index
    return {
        "format": FORMAT,
        "fields": list(schema.field_names()),
        "docs": [serializer.to_dict(index.docs[i]) for i in sorted(index.docs)],
    }


def load(data):
    """Rebuild a Searcher from `dump` output. Snapshots written before a field existed still load."""
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise SnapshotError("not a snapshot this version can read", field="format")
    unknown = [f for f in data.get("fields", []) if f not in schema.FIELDS]
    if unknown:
        raise SnapshotError(f"snapshot has a field this version does not know: {unknown[0]!r}", field="fields")
    searcher = Searcher()
    for item in data.get("docs", []):
        searcher.add(serializer.from_dict(item))
    return searcher


def dumps(searcher):
    return json.dumps(dump(searcher), sort_keys=False)


def loads(text):
    try:
        return load(json.loads(text))
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"snapshot is not valid JSON: {exc.msg}", field="snapshot") from None
