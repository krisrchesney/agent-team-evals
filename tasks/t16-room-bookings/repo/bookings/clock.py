"""A clock the service reads 'now' from, so tests can control time."""
from datetime import datetime, timedelta


class Clock:
    def __init__(self, now=None):
        self._now = now or datetime(2024, 6, 3, 8, 0)

    def now(self):
        return self._now

    def set(self, now):
        self._now = now

    def advance(self, **kwargs):
        self._now += timedelta(**kwargs)
