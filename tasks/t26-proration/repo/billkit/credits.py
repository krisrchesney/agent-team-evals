"""Account credit: money we owe a customer that is taken off their next invoices."""
from dataclasses import dataclass

from .errors import Conflict, ValidationError


@dataclass
class CreditEntry:
    customer: str
    delta_cents: int
    reason: str


class CreditLedger:
    def __init__(self):
        self.entries = []

    def add(self, customer_id, cents, reason):
        if not isinstance(cents, int) or cents <= 0:
            raise ValidationError("cents must be a positive whole number", field="cents")
        self.entries.append(CreditEntry(customer_id, cents, reason))

    def balance(self, customer_id):
        return sum(e.delta_cents for e in self.entries if e.customer == customer_id)

    def spend(self, customer_id, cents, reason):
        if cents > self.balance(customer_id):
            raise Conflict("not enough credit", field="cents")
        self.entries.append(CreditEntry(customer_id, -cents, reason))

    def apply_to_invoice(self, invoice):
        """Use credit up to the invoice total; returns the cents that were applied."""
        usable = min(self.balance(invoice.customer), max(invoice.total_cents, 0))
        if usable:
            self.spend(invoice.customer, usable, f"applied to {invoice.id}")
        return usable

    def history(self, customer_id):
        return [e for e in self.entries if e.customer == customer_id]
