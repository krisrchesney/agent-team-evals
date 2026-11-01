from .views import stamp


class Outbox:
    """One tenant's events waiting to be picked up, numbered from 1 within the tenant.

    Subscribers (shared by every tenant) see each event as it is emitted; `drain` hands over the rest.
    """

    def __init__(self, clock, tenant, subscribers):
        self.clock = clock
        self.tenant = tenant
        self.events = []
        self.subscribers = subscribers
        self._seq = 0

    def emit(self, type_, data):
        self._seq += 1
        event = {"seq": self._seq, "tenant": self.tenant, "type": type_, "at": stamp(self.clock.now()),
                 "data": data}
        self.events.append(event)
        for fn in self.subscribers:
            fn(dict(event))

    def drain(self):
        """Every event not yet drained, oldest first; they are removed."""
        taken, self.events = self.events, []
        return taken
