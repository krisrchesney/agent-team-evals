from datetime import datetime, timedelta, timezone


class SystemClock:
    def now(self):
        return datetime.now(timezone.utc).replace(microsecond=0)


class FixedClock:
    """A clock that only moves when told to. Tests use it."""

    def __init__(self, start=None):
        self._now = start or datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)

    def now(self):
        return self._now

    def advance(self, **delta):
        self._now += timedelta(**delta)
