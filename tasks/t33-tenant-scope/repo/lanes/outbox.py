from .views import stamp


class Outbox:
    """Events waiting to be picked up. Subscribers see each event as it is emitted; `drain` hands over the rest."""

    def __init__(self, clock):
        self.clock = clock
        self.events = []
        self.subscribers = []
        self._seq = 0

    def emit(self, type_, data):
        self._seq += 1
        event = {"seq": self._seq, "type": type_, "at": stamp(self.clock.now()), "data": data}
        self.events.append(event)
        for fn in self.subscribers:
            fn(dict(event))

    def drain(self):
        """Every event not yet drained, oldest first; they are removed."""
        taken, self.events = self.events, []
        return taken
