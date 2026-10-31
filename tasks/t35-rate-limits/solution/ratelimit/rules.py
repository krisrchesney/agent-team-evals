"""The two algorithms. A rule is pure: it never touches a store or a clock. See docs/SPEC.md."""
from .decision import Decision


def _check_int(value, name, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError("%s must be an int >= %d" % (name, minimum))


def _check_positive(value, name):
    if type(value) is bool or not isinstance(value, (int, float)) or not value > 0:
        raise ValueError("%s must be a number > 0" % name)


class TokenBucket:
    def __init__(self, capacity, refill_per_sec):
        _check_int(capacity, "capacity")
        _check_positive(refill_per_sec, "refill_per_sec")
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec

    def _current(self, state, now, max_skew):
        if state is None:
            return float(self.capacity), now
        tokens, updated = state["tokens"], state["updated"]
        if updated > now + max_skew:
            updated = now
        elapsed = max(0, now - updated)
        tokens = min(self.capacity, tokens + elapsed * self.refill_per_sec)
        return tokens, max(updated, now)

    def evaluate(self, state, now, cost, max_skew):
        _check_int(cost, "cost")
        tokens, updated = self._current(state, now, max_skew)
        if cost > self.capacity:
            allowed, retry = False, None
        elif tokens >= cost:
            allowed, retry = True, 0.0
            tokens -= cost
        else:
            allowed, retry = False, (cost - tokens) / self.refill_per_sec
        decision = Decision(allowed, self.capacity, int(tokens), retry,
                            (self.capacity - tokens) / self.refill_per_sec)
        return decision, {"tokens": tokens, "updated": updated}

    def is_idle(self, state, now, max_skew):
        tokens, _ = self._current(state, now, max_skew)
        return tokens == self.capacity


class SlidingWindow:
    def __init__(self, limit, window):
        _check_int(limit, "limit")
        _check_positive(window, "window")
        self.limit = limit
        self.window = window

    def _current(self, state, now, max_skew):
        hits = list(state["hits"]) if state else []
        hits = [t for t in hits if t > now - self.window]
        hits = [now if t > now + max_skew else t for t in hits]
        return sorted(hits)

    def evaluate(self, state, now, cost, max_skew):
        _check_int(cost, "cost")
        hits = self._current(state, now, max_skew)
        count = len(hits)
        if cost > self.limit:
            allowed, retry = False, None
        elif count + cost <= self.limit:
            allowed, retry = True, 0.0
            hits = sorted(hits + [now] * cost)
        else:
            allowed = False
            retry = max(0.0, hits[count + cost - self.limit - 1] + self.window - now)
        reset = max(0.0, hits[-1] + self.window - now) if hits else 0.0
        decision = Decision(allowed, self.limit, max(0, self.limit - len(hits)), retry, reset)
        return decision, {"hits": hits}

    def is_idle(self, state, now, max_skew):
        return not self._current(state, now, max_skew)
