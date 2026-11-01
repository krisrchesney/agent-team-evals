from .base import Meter
from .registry import meter


@meter
class Units(Meter):
    """Every unit costs PRICE_MILLS."""
    name = "units"
    priority = 20
    PRICE_MILLS = 125

    def record(self, customer, quantity):
        self.usage[customer] = self.get(customer) + quantity

    def settle(self, customer):
        used = self.get(customer)
        if used == 0:
            return []
        return [self.line(used, self.cents(used * self.PRICE_MILLS))]
