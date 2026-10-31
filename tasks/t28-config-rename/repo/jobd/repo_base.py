"""A tiny in-memory repository: ids, save, get, all, delete."""
from .errors import NotFound


class Repository:
    prefix = "rec"
    noun = "record"

    def __init__(self):
        self._items = {}
        self._counter = 0

    def next_id(self):
        self._counter += 1
        return f"{self.prefix}_{self._counter:04d}"

    def save(self, record):
        self._items[record.id] = record
        return record

    def get(self, record_id):
        try:
            return self._items[record_id]
        except KeyError:
            raise NotFound(f"no {self.noun} {record_id!r}", field="id") from None

    def all(self):
        return list(self._items.values())

    def delete(self, record_id):
        self.get(record_id)
        del self._items[record_id]

    def __len__(self):
        return len(self._items)

    def __contains__(self, record_id):
        return record_id in self._items
