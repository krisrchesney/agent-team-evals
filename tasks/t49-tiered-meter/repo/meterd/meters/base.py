from ..errors import Conflict


class Meter:
    """Base class of every meter.

    usage.record calls record(customer, quantity) on the meter it names. period.close calls settle()
    on every meter in priority order (lower number first), collects the invoice lines, and then calls
    forget() on every meter, so the next period starts empty. A meter keeps a customer's usage for the
    current period in `self.usage`, read through get(); forget() is what clears it, and anything kept
    elsewhere is not cleared.

    Prices are worked out in mills (a tenth of a cent) and turned into cents once, on the whole line,
    by cents().
    """
    name = None
    priority = 50

    def __init__(self):
        self.usage = {}

    def fresh(self):
        """A customer's usage at the start of a period."""
        return 0

    def get(self, customer):
        return self.usage.setdefault(customer, self.fresh())

    def record(self, customer, quantity):
        raise Conflict(f"meter {self.name!r} does not take usage", param="meter")

    def settle(self, customer):
        """The invoice lines for this meter, as a list. Nothing owed means no line."""
        return []

    def forget(self, customer):
        self.usage.pop(customer, None)

    @staticmethod
    def cents(mills):
        """Mills to cents, half a cent rounding up."""
        return (mills + 5) // 10

    def line(self, quantity, amount):
        return {"meter": self.name, "quantity": quantity, "amount": amount}
