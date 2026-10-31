"""The two algorithms. A rule is pure: it never touches a store or a clock. See docs/SPEC.md."""


class TokenBucket:
    def __init__(self, capacity, refill_per_sec):
        raise NotImplementedError

    def evaluate(self, state, now, cost, max_skew):
        """Return (Decision, new_state). `state` is None for a key never seen; it must not be mutated."""
        raise NotImplementedError

    def is_idle(self, state, now, max_skew):
        raise NotImplementedError


class SlidingWindow:
    def __init__(self, limit, window):
        raise NotImplementedError

    def evaluate(self, state, now, cost, max_skew):
        raise NotImplementedError

    def is_idle(self, state, now, max_skew):
        raise NotImplementedError
