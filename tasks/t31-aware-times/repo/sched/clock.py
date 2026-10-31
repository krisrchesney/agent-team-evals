from datetime import datetime, timedelta


class SystemClock:
    def now(self):
        return datetime.now().replace(second=0, microsecond=0)


class FixedClock:
    """A clock that only moves when told to. Tests use it."""

    def __init__(self, start=None):
        self._now = start or datetime(2026, 3, 1, 8, 0)

    def now(self):
        return self._now

    def advance(self, **delta):
        self._now += timedelta(**delta)
