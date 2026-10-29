"""A small least-recently-used cache with optional TTL."""
import time
from collections import OrderedDict

_DEFAULT = object()


class LRUCache:
    def __init__(self, capacity, ttl=None, clock=time.monotonic):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self.ttl = ttl
        self._clock = clock
        self._data = OrderedDict()  # key -> (value, expires_at or None)

    @staticmethod
    def _expired(entry, now):
        return entry[1] is not None and now >= entry[1]

    def _live(self, key):
        entry = self._data.get(key)
        if entry is None:
            return None
        if self._expired(entry, self._clock()):
            del self._data[key]
            return None
        return entry

    def get(self, key, default=None):
        entry = self._live(key)
        if entry is None:
            return default
        self._data.move_to_end(key)
        return entry[0]

    def set(self, key, value, ttl=_DEFAULT):
        ttl = self.ttl if ttl is _DEFAULT else ttl
        expires = None if ttl is None else self._clock() + ttl
        if key in self._data:
            del self._data[key]
        elif len(self._data) >= self.capacity:
            self.purge_expired()
            if len(self._data) >= self.capacity:
                self._data.popitem(last=False)
        self._data[key] = (value, expires)

    def purge_expired(self):
        now = self._clock()
        dead = [k for k, e in self._data.items() if self._expired(e, now)]
        for k in dead:
            del self._data[k]
        return len(dead)

    def __contains__(self, key):
        return self._live(key) is not None

    def __len__(self):
        now = self._clock()
        return sum(1 for e in self._data.values() if not self._expired(e, now))
