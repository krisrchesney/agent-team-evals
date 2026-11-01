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
        """Run one operation. Every operation follows the same conventions:

        - Read `now` once from `self.clock`. Validate every argument and check every rule before changing
          anything. A call that raises changes nothing: no record touched, no id taken, no event.
        - Take ids from `self.ids` only once the call can no longer fail.
        - A record that changes gets `store.bump(record, now)`: version + 1, updated_at = now.
        - Emit exactly one event, last: `<noun>.<operation in the past tense>` (`loan.borrow` is
          `loan.borrowed`), with data `{"<noun>": view}` where `view` is the one the call returns. Other
          records the call changes along the way change silently. Reads emit nothing.
        """
        fn = registry.OPERATIONS.get(operation)
        if fn is None:
            raise UnknownOperation(f"no operation {operation!r}", param="operation")
        return fn(self, params)

    def operations(self):
        return sorted(registry.OPERATIONS)
