from .clock import SystemClock
from .errors import UnknownOperation
from .events import Bus
from .ids import Ids
from .ops import registry
from .store import Store


class Service:
    def __init__(self, clock=None):
        self.clock = clock or SystemClock()
        self.store = Store()
        self.bus = Bus()
        self.ids = Ids()

    def call(self, operation, **params):
        fn = registry.OPERATIONS.get(operation)
        if fn is None:
            raise UnknownOperation(f"no operation {operation!r}", param="operation")
        return fn(self, params)

    def operations(self):
        return sorted(registry.OPERATIONS)
