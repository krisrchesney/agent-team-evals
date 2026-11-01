from ..errors import Conflict


class Reaction:
    """Base class of every reaction.

    Every order move runs each reaction twice, in priority order (lower number first): check() before
    anything changes, where a reaction may refuse the move, and apply() once the order has its new
    status, which returns the events the reaction wants to add, as (type, data) pairs. The move's own
    `order.<status>` event goes out first, then the reactions' events in the same priority order.

    Reactions that count things per day keep them in `self.state`. The service calls begin_day() on
    every reaction at the first call of each new day, which replaces the state with a fresh() one.
    Anything kept elsewhere is not cleared.
    """
    priority = 50

    def __init__(self):
        self.state = self.fresh()

    def fresh(self):
        """The state for one day."""
        return {}

    def begin_day(self, day):
        self.state = self.fresh()

    def check(self, svc, order, action):
        pass

    def apply(self, svc, order, action):
        return []

    def refuse(self, reason):
        raise Conflict(reason, param="order")
