"""The document model."""
from dataclasses import dataclass, field

from .errors import ValidationError

MAX_TAGS = 20


@dataclass
class Document:
    id: str
    title: str = ""
    body: str = ""
    tags: list = field(default_factory=list)
    updated: str = ""


def clean_text(value, name, limit):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string", field=name)
    value = " ".join(value.split())
    if len(value) > limit:
        raise ValidationError(f"{name} is longer than {limit} characters", field=name)
    return value


def clean_tags(value):
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValidationError("tags must be a list", field="tags")
    tags = []
    for tag in value:
        tag = clean_text(tag, "tags", 40)
        if tag and tag not in tags:
            tags.append(tag)
    if len(tags) > MAX_TAGS:
        raise ValidationError(f"a document can have at most {MAX_TAGS} tags", field="tags")
    return tags


def make(doc_id, title="", body="", tags=None, updated=""):
    """Build a validated document. Text is trimmed and whitespace is collapsed."""
    if not isinstance(doc_id, str) or not doc_id.strip():
        raise ValidationError("id is required", field="id")
    return Document(
        id=doc_id.strip(),
        title=clean_text(title, "title", 200),
        body=clean_text(body, "body", 100000),
        tags=clean_tags(tags),
        updated=clean_text(updated, "updated", 40),
    )


def field_values(doc):
    """What gets indexed: a list of strings for each indexed field (tags can have several)."""
    return {
        "title": [doc.title],
        "body": [doc.body],
        "tags": list(doc.tags),
    }
