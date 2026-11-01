"""The limiter ties rules, a store and a clock together. See docs/SPEC.md."""
from .clock import SystemClock
from .store import MemoryStore


class Limiter:
    def __init__(self, rules, store=None, clock=None, max_skew=2.0):
        self.rules = dict(rules)
        self.store = store if store is not None else MemoryStore()
        self.clock = clock or SystemClock()
        self.max_skew = max_skew

    def hit(self, rule, key, cost=1):
        raise NotImplementedError

    def peek(self, rule, key, cost=1):
        raise NotImplementedError

    def hit_all(self, pairs, cost=1):
        raise NotImplementedError

    def reset(self, rule, key=None):
        raise NotImplementedError

    def purge(self):
        raise NotImplementedError
