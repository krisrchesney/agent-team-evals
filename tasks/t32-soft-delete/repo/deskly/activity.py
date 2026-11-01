from .views import stamp


class Feed:
    """The history of everything that happened, oldest first. It is a log: nothing is ever hidden from it."""

    def __init__(self, clock):
        self.clock = clock
        self.events = []

    def record(self, type_, data):
        self.events.append({"seq": len(self.events) + 1, "type": type_, "at": stamp(self.clock.now()),
                            "data": data})

    def recent(self, limit=20):
        """The newest `limit` events, newest first."""
        return [dict(e) for e in reversed(self.events[-limit:])]
