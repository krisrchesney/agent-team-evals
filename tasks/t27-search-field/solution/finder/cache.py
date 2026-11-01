"""A small LRU cache of search results."""
from collections import OrderedDict

# One bit per field, so the set of fields searched fits in a small integer inside a cache key.
FIELD_BITS = {"title": 1, "body": 2, "tags": 4, "author": 8}
ALL_FIELDS_MASK = 0xFF


def fields_mask(fields):
    """Bit mask of a list of field names; None means "every field"."""
    if fields is None:
        return ALL_FIELDS_MASK
    mask = 0
    for name in fields:
        mask |= FIELD_BITS[name]
    return mask


def make_key(canon_query, fields, limit, offset, highlight, generation):
    """Two requests that must return the same results have the same key."""
    return (canon_query, fields_mask(fields), limit, offset, bool(highlight), generation)


class ResultCache:
    def __init__(self, capacity=128):
        self.capacity = capacity
        self._items = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        if key in self._items:
            self._items.move_to_end(key)
            self.hits += 1
            return self._items[key]
        self.misses += 1
        return None

    def put(self, key, value):
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def clear(self):
        self._items.clear()

    def __len__(self):
        return len(self._items)

    def stats(self):
        return {"hits": self.hits, "misses": self.misses, "size": len(self._items)}
