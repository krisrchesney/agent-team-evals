"""The limiter ties rules, a store and a clock together. See docs/SPEC.md."""
from .clock import SystemClock
from .errors import UnknownRule
from .store import MemoryStore


class Limiter:
    def __init__(self, rules, store=None, clock=None, max_skew=2.0):
        self.rules = dict(rules)
        self.store = store if store is not None else MemoryStore()
        self.clock = clock or SystemClock()
        self.max_skew = max_skew

    def _rule(self, rule, key):
        if rule not in self.rules:
            raise UnknownRule("unknown rule %r" % (rule,))
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty str")
        return self.rules[rule]

    def _evaluate(self, rule, key, cost, now):
        return self._rule(rule, key).evaluate(self.store.get(rule, key), now, cost, self.max_skew)

    def hit(self, rule, key, cost=1):
        self._rule(rule, key)
        now = self.clock.now()
        decision, state = self._evaluate(rule, key, cost, now)
        self.store.set(rule, key, state)
        return decision

    def peek(self, rule, key, cost=1):
        self._rule(rule, key)
        decision, _ = self._evaluate(rule, key, cost, self.clock.now())
        return decision

    def hit_all(self, pairs, cost=1):
        pairs = [tuple(p) for p in pairs]
        if not pairs or len(set(pairs)) != len(pairs):
            raise ValueError("pairs must be a non-empty list without repeats")
        for rule, key in pairs:
            self._rule(rule, key)
        now = self.clock.now()
        results = [(rule, key) + self._evaluate(rule, key, cost, now) for rule, key in pairs]
        denied = [r[2] for r in results if not r[2].allowed]
        if denied:
            best = denied[0]
            for d in denied[1:]:
                if self._worse(d, best):
                    best = d
            return best
        for rule, key, _, state in results:
            self.store.set(rule, key, state)
        best = results[0][2]
        for r in results[1:]:
            if r[2].remaining < best.remaining:
                best = r[2]
        return best

    @staticmethod
    def _worse(a, b):
        if a.retry_after is None:
            return b.retry_after is not None
        return b.retry_after is not None and a.retry_after > b.retry_after

    def reset(self, rule, key=None):
        if rule not in self.rules:
            raise UnknownRule("unknown rule %r" % (rule,))
        if key is None:
            self.store.delete_rule(rule)
        else:
            self._rule(rule, key)
            self.store.delete(rule, key)

    def purge(self):
        now = self.clock.now()
        removed = 0
        for name, rule in self.rules.items():
            for key in self.store.keys(name):
                if rule.is_idle(self.store.get(name, key), now, self.max_skew):
                    self.store.delete(name, key)
                    removed += 1
        return removed
