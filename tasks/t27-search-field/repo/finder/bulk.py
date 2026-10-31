"""Loading many documents at once."""
from dataclasses import dataclass, field

from . import serializer
from .errors import Conflict, FinderError


@dataclass
class BulkReport:
    added: int = 0
    updated: int = 0
    failed: list = field(default_factory=list)  # [(line number, message)]

    @property
    def ok(self):
        return not self.failed


def load_jsonl(searcher, text, replace=False):
    """Index every document in a JSON-lines text. Bad lines are reported and skipped."""
    report = BulkReport()
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            docs = serializer.loads(line)
            for doc in docs:
                if doc.id in searcher.index and replace:
                    searcher.update(doc)
                    report.updated += 1
                else:
                    searcher.add(doc)
                    report.added += 1
        except Conflict as exc:
            report.failed.append((number, f"duplicate: {exc.message}"))
        except FinderError as exc:
            report.failed.append((number, exc.message))
    return report


def dump_jsonl(searcher):
    return serializer.dumps(searcher.index.docs[i] for i in sorted(searcher.index.docs))
