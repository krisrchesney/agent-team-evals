"""Adding and removing seats during a period."""
from dataclasses import dataclass

from . import periods
from .constants import MAX_SEATS
from .errors import Conflict, ValidationError
from .invoices import Line


@dataclass
class SeatChange:
    subscription: str
    quantity: int
    charge_cents: int
    invoice: str = None


def add_seats(app, sub_id, count, on):
    """New seats are charged for the rest of the current period, halves rounded up."""
    sub = app.subscriptions.get(sub_id)
    if sub.status != "active":
        raise Conflict("subscription is not active", field="subscription")
    if not isinstance(count, int) or count < 1:
        raise ValidationError("count must be a positive whole number", field="count")
    if sub.quantity + count > MAX_SEATS:
        raise Conflict(f"a subscription can have at most {MAX_SEATS} seats", field="count")
    plan = app.catalog.get(sub.plan)
    start, end = periods.period_for(sub, on, plan.interval)
    remaining = (end - on).days
    basis = 30 * (12 if plan.interval == "year" else 1)
    charge = (2 * plan.price_cents * count * min(remaining, basis) + basis) // (2 * basis)
    line = Line(f"{count} extra seat(s) on {plan.name}", charge, on, end, "proration")
    invoice = app.invoices.issue(app, sub.customer, sub.id, [line], on)
    sub.quantity += count
    app.events.emit("subscription.seats_added", sub.id, count=count)
    return SeatChange(sub.id, sub.quantity, charge, invoice.id)


def remove_seats(app, sub_id, count):
    """Removing seats takes effect now and is never refunded."""
    sub = app.subscriptions.get(sub_id)
    if not isinstance(count, int) or count < 1:
        raise ValidationError("count must be a positive whole number", field="count")
    if sub.quantity - count < 1:
        raise Conflict("a subscription needs at least one seat", field="count")
    sub.quantity -= count
    app.events.emit("subscription.seats_removed", sub.id, count=count)
    return SeatChange(sub.id, sub.quantity, 0)
