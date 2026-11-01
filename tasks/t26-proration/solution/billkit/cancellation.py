"""Cancelling a subscription and refunding the unused time."""
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from . import periods
from .errors import Conflict
from .invoices import Line


@dataclass
class Cancellation:
    subscription: str
    refund_cents: int
    credit_note: str = None


def cancel(app, sub_id, on):
    """End the subscription today. The unused days are refunded, rounded down to the cent."""
    sub = app.subscriptions.get(sub_id)
    if sub.status != "active":
        raise Conflict("subscription is already canceled", field="subscription")
    plan = app.catalog.get(sub.plan)
    start, end = periods.period_for(sub, on, plan.interval)
    unused = (end - on).days
    basis = (end - start).days
    paid = Decimal(plan.price_cents * sub.quantity)
    refund = int((paid * unused / basis).to_integral_value(rounding=ROUND_DOWN))
    sub.status = "canceled"
    sub.canceled_on = on
    note = None
    if refund > 0:
        line = Line(f"Refund for unused time on {plan.name}", -refund, on, end, "refund")
        note = app.invoices.issue(app, sub.customer, sub.id, [line], on, kind="credit_note").id
    app.events.emit("subscription.canceled", sub.id, refund_cents=refund)
    return Cancellation(sub.id, refund, note)
