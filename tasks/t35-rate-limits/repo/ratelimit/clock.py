"""Clocks return seconds as a float (like time.time())."""
import time


class SystemClock:
    def now(self):
        return time.time()


class FixedClock:
    def __init__(self, start=1000.0):
        self._now = float(start)

    def now(self):
        return self._now

    def advance(self, seconds):
        self._now += seconds

    def set(self, value):
        self._now = float(value)
