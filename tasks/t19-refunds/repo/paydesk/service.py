"""The service object every operation receives as `svc`."""
import datetime
import itertools

from . import ops
from .audit import AuditLog
from .errors import Forbidden, NotFound
from .events import EventBus
from .idempotency import IdempotencyStore
from .ledger import Ledger
from .store import Store


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _counter_ids():
    counter = itertools.count(1)
    return lambda prefix: f"{prefix}_{next(counter):06d}"


class Service:
    def __init__(self, *, clock=None, ids=None):
        """clock() returns the current time as an ISO string; ids(prefix) returns a new id."""
        ops.load()
        self._clock = clock or _utc_now
        self._ids = ids or _counter_ids()
        self.store = Store()
        self.ledger = Ledger()
        self.audit = AuditLog()
        self.events = EventBus()
        self.idempotency = IdempotencyStore()

    def now(self):
        return self._clock()

    def new_id(self, prefix):
        return self._ids(prefix)

    def call(self, name, ctx, **params):
        try:
            fn, scope = ops.OPERATIONS[name]
        except KeyError:
            raise NotFound(f"no such operation: {name}", code="unknown_operation") from None
        if scope not in ctx.scopes:
            raise Forbidden(f"{ctx.actor} lacks scope {scope} for {name}", code="forbidden")
        return fn(self, ctx, **params)
