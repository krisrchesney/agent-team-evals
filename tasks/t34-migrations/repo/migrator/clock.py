"""Clocks return timezone-aware UTC datetimes. `iso` formats one the way the runner stores times."""
from datetime import datetime, timedelta, timezone


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SystemClock:
    def now(self):
        return datetime.now(timezone.utc)


class FixedClock:
    def __init__(self, start=None):
        self._now = start or datetime(2026, 3, 2, 8, 0, 0, tzinfo=timezone.utc)

    def now(self):
        return self._now

    def advance(self, **kwargs):
        self._now += timedelta(**kwargs)
