"""Clocks: the real one, and a fake one for tests."""
import time


class RealClock:
    def now(self):
        return time.monotonic()

    def sleep(self, seconds):
        time.sleep(seconds)


class FakeClock:
    """A clock that only moves when somebody sleeps."""

    def __init__(self, start=0.0):
        self._now = start

    def now(self):
        return self._now

    def sleep(self, seconds):
        if seconds < 0:
            raise ValueError("cannot sleep a negative time")
        self._now += seconds
