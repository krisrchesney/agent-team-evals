"""A log of searches, for finding what people look for and cannot find."""
from collections import Counter
from dataclasses import dataclass


@dataclass
class Entry:
    query: str
    total: int
    at: str


class QueryLog:
    def __init__(self, keep=1000):
        self.keep = keep
        self.entries = []

    def record(self, query, total, at=""):
        self.entries.append(Entry(query.strip(), total, at))
        if len(self.entries) > self.keep:
            del self.entries[: len(self.entries) - self.keep]

    def top(self, n=10):
        counts = Counter(e.query.casefold() for e in self.entries)
        return counts.most_common(n)

    def zero_results(self, n=10):
        counts = Counter(e.query.casefold() for e in self.entries if e.total == 0)
        return counts.most_common(n)

    def average_results(self):
        if not self.entries:
            return 0.0
        return sum(e.total for e in self.entries) / len(self.entries)

    def clear(self):
        self.entries.clear()
