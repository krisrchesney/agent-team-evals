from .base import Meter
from .registry import meter


@meter
class Flat(Meter):
    """The monthly platform fee. Every invoice has it, and it takes no usage."""
    name = "flat"
    priority = 10
    FEE_CENTS = 500

    def settle(self, customer):
        return [self.line(1, self.FEE_CENTS)]
