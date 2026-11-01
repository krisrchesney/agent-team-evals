from .base import Meter
from .registry import meter


@meter
class Tiered(Meter):
    """Volume pricing: each unit costs the price of the tier it falls in. TIERS are (units up to, mills)."""
    name = "tiered"
    priority = 40
    TIERS = ((100, 75), (1000, 62), (None, 45))

    def record(self, customer, quantity):
        self.usage[customer] = self.get(customer) + quantity

    def settle(self, customer):
        used = self.get(customer)
        if used == 0:
            return []
        mills, floor = 0, 0
        for limit, price in self.TIERS:
            top = used if limit is None else min(used, limit)
            if top > floor:
                mills += (top - floor) * price
            if limit is not None:
                floor = limit
        return [self.line(used, self.cents(mills))]
