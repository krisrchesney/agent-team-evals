"""Invoices and credit notes. A credit note is an invoice whose lines are negative."""
from dataclasses import dataclass, field
from datetime import date, timedelta

from .constants import INVOICE_DUE_DAYS
from .errors import Conflict
from .money import basis_points_of
from .repo_base import Repository


@dataclass
class Line:
    description: str
    amount_cents: int
    period_start: date
    period_end: date
    kind: str = "subscription"


@dataclass
class Invoice:
    id: str
    customer: str
    subscription: str
    kind: str
    issued_on: date
    due_on: date
    lines: list = field(default_factory=list)
    tax_cents: int = 0
    paid_on: date = None

    @property
    def subtotal_cents(self):
        return sum(line.amount_cents for line in self.lines)

    @property
    def total_cents(self):
        return self.subtotal_cents + self.tax_cents


class InvoiceBook(Repository):
    prefix = "inv"
    noun = "invoice"

    def issue(self, app, customer_id, subscription_id, lines, on, kind="invoice"):
        customer = app.customers.get(customer_id)
        subtotal = sum(line.amount_cents for line in lines)
        invoice = Invoice(
            id=self.next_id(),
            customer=customer_id,
            subscription=subscription_id,
            kind=kind,
            issued_on=on,
            due_on=on + timedelta(days=INVOICE_DUE_DAYS),
            lines=list(lines),
            tax_cents=tax_for(app, customer, subtotal),
        )
        self.save(invoice)
        app.events.emit(f"{kind}.issued", invoice.id, customer=customer_id)
        return invoice

    def for_subscription(self, subscription_id):
        return [i for i in self.all() if i.subscription == subscription_id]

    def for_customer(self, customer_id):
        return [i for i in self.all() if i.customer == customer_id]

    def unpaid(self):
        return [i for i in self.all() if i.kind == "invoice" and i.paid_on is None]

    def pay(self, invoice_id, on):
        invoice = self.get(invoice_id)
        if invoice.kind != "invoice":
            raise Conflict("only invoices can be paid", field="id")
        if invoice.paid_on is not None:
            raise Conflict("invoice is already paid", field="id")
        invoice.paid_on = on
        return invoice


def tax_for(app, customer, subtotal_cents):
    """Tax on a subtotal, from the tax rate of the customer's region (none if the region has no rate)."""
    rates = app.tax_rates.find_by_region(customer.region) if customer.region else []
    if not rates:
        return 0
    return basis_points_of(subtotal_cents, rates[0].bps)
