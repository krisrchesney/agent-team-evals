from .views import stamp


class Audit:
    """A record of every change. It is never drained."""

    def __init__(self, clock):
        self.clock = clock
        self.entries = []

    def record(self, action, target, detail=None):
        self.entries.append({"seq": len(self.entries) + 1, "at": stamp(self.clock.now()), "action": action,
                             "target": target, "detail": detail})

    def recent(self, limit=20):
        """The newest `limit` entries, newest first."""
        return [dict(e) for e in reversed(self.entries[-limit:])]
