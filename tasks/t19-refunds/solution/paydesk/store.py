"""In-memory storage. The production adapter has the same interface."""
from .errors import NotFound


class Store:
    def __init__(self):
        self.charges = {}
        self.refunds = {}

    def get_charge(self, charge_id):
        try:
            return self.charges[charge_id]
        except KeyError:
            raise NotFound(f"no such charge: {charge_id}", code="not_found", param="charge_id") from None

    def add_charge(self, charge):
        self.charges[charge.id] = charge

    def get_refund(self, refund_id):
        try:
            return self.refunds[refund_id]
        except KeyError:
            raise NotFound(f"no such refund: {refund_id}", code="not_found", param="refund_id") from None

    def add_refund(self, refund):
        self.refunds[refund.id] = refund
