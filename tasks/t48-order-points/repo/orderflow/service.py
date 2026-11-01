from .clock import SystemClock
from .errors import UnknownOperation
from .events import Bus
from .ids import Ids
from .ops import registry
from .reactions import registry as reaction_registry
from .store import Store


class Service:
    def __init__(self, clock=None):
        self.clock = clock or SystemClock()
        self.store = Store()
        self.bus = Bus()
        self.ids = Ids()
        self.reactions = reaction_registry.build()
        self.day = None

    def call(self, operation, **params):
        fn = registry.OPERATIONS.get(operation)
        if fn is None:
            raise UnknownOperation(f"no operation {operation!r}", param="operation")
        self._roll_day()
        return fn(self, params)

    def _roll_day(self):
        """The first call on a new day tells every reaction, so their daily state starts empty."""
        today = self.clock.now().date()
        if today != self.day:
            self.day = today
            for reaction in self.reactions:
                reaction.begin_day(today)

    def operations(self):
        return sorted(registry.OPERATIONS)
