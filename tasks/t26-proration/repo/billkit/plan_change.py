"""Moving a subscription to another plan in the middle of a period."""
from dataclasses import dataclass
from decimal import Decimal

from . import periods
from .constants import DAYS_PER_MONTH, MONTHS_PER_YEAR
from .errors import Conflict
from .invoices import Line
from .money import round_cents


@dataclass
class PlanChange:
    subscription: str
    old_plan: str
    new_plan: str
    credit_cents: int
    charge_cents: int
    invoice: str

    @property
    def net_cents(self):
        return self.charge_cents - self.credit_cents


def change_plan(app, sub_id, new_plan_id, on):
    """Credit the unused part of the old plan and charge the rest of the period at the new price."""
    sub = app.subscriptions.get(sub_id)
    if sub.status != "active":
        raise Conflict("subscription is not active", field="subscription")
    old = app.catalog.get(sub.plan)
    new = app.catalog.get(new_plan_id)
    if new.interval != old.interval:
        raise Conflict("cannot switch between monthly and yearly plans", field="plan")
    start, end = periods.period_for(sub, on, old.interval)
    remaining = (end - on).days
    basis = DAYS_PER_MONTH if old.interval == "month" else MONTHS_PER_YEAR * DAYS_PER_MONTH
    fraction = Decimal(min(remaining, basis)) / Decimal(basis)
    credit = round_cents(old.price_cents * sub.quantity * fraction)
    charge = round_cents(new.price_cents * sub.quantity * fraction)
    lines = [
        Line(f"Unused time on {old.name}", -credit, on, end, "proration"),
        Line(f"Remaining time on {new.name}", charge, on, end, "proration"),
    ]
    invoice = app.invoices.issue(app, sub.customer, sub.id, lines, on)
    sub.plan = new.id
    app.events.emit("subscription.plan_changed", sub.id, old=old.id, new=new.id)
    return PlanChange(sub.id, old.id, new.id, credit, charge, invoice.id)
