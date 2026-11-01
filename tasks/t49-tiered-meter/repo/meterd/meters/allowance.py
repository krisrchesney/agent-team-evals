from .base import Meter
from .registry import meter


@meter
class Allowance(Meter):
    """The first FREE units of a period cost nothing; every unit after that costs PRICE_MILLS."""
    name = "allowance"
    priority = 30
    FREE = 1000
    PRICE_MILLS = 15

    def record(self, customer, quantity):
        self.usage[customer] = self.get(customer) + quantity

    def settle(self, customer):
        used = self.get(customer)
        extra = max(0, used - self.FREE)
        if extra == 0:
            return []
        return [self.line(used, self.cents(extra * self.PRICE_MILLS))]
