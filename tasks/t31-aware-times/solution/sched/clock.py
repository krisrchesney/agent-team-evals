from datetime import datetime, timedelta, timezone


class SystemClock:
    def now(self):
        return datetime.now(timezone.utc).replace(second=0, microsecond=0)


class FixedClock:
    """A clock that only moves when told to. Tests use it. A naive start is read as UTC."""

    def __init__(self, start=None):
        start = start or datetime(2026, 3, 1, 8, 0)
        self._now = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start.astimezone(timezone.utc)

    def now(self):
        return self._now

    def advance(self, **delta):
        self._now += timedelta(**delta)
