"""Documents to and from plain dicts and JSON lines.

Stored documents outlive code changes, so `from_dict` accepts dicts written by older versions:
anything optional that is missing gets its default.
"""
import json

from .documents import Document, make
from .errors import ValidationError

FIELD_ORDER = ("id", "title", "body", "tags", "author", "updated")


def to_dict(doc):
    values = {
        "id": doc.id,
        "title": doc.title,
        "body": doc.body,
        "tags": list(doc.tags),
        "author": doc.author,
        "updated": doc.updated,
    }
    return {name: values[name] for name in FIELD_ORDER}


def from_dict(data):
    if not isinstance(data, dict):
        raise ValidationError("a document must be an object", field="document")
    if "id" not in data:
        raise ValidationError("id is required", field="id")
    return make(
        data["id"],
        title=data.get("title", ""),
        body=data.get("body", ""),
        tags=data.get("tags", []),
        updated=data.get("updated", ""),
        author=data.get("author", ""),
    )


def dumps(docs):
    """One JSON object per line, in the order given."""
    return "".join(json.dumps(to_dict(d), sort_keys=False) + "\n" for d in docs)


def loads(text):
    docs = []
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"line {number}: {exc.msg}", field="document") from None
        docs.append(from_dict(data))
    return docs


def copy(doc: Document) -> Document:
    return from_dict(to_dict(doc))
