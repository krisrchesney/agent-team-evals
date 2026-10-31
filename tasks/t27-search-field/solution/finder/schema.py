"""The indexed fields of a document and how each one is analysed and weighted."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    name: str
    analyzer: str  # a key of finder.analysis.analyzers.ANALYZERS
    boost: float   # how much a match in this field adds to a document's score


FIELDS = {
    "title": Field("title", "text", 3.0),
    "body": Field("body", "text", 1.0),
    "tags": Field("tags", "words", 2.0),
    "author": Field("author", "words", 1.5),
}


def field_names():
    return tuple(FIELDS)


def get(name):
    return FIELDS[name]


def default_fields():
    """The fields an unqualified term is looked up in."""
    return field_names()
