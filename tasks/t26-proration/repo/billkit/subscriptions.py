"""Subscriptions: a customer on a plan, with a number of seats."""
from dataclasses import dataclass
from datetime import date

from . import invoicing
from .constants import MAX_SEATS
from .errors import ValidationError
from .repo_base import Repository


@dataclass
class Subscription:
    id: str
    customer: str
    plan: str
    quantity: int
    start: date
    anchor_day: int
    status: str = "active"
    canceled_on: date = None


class SubscriptionRepo(Repository):
    prefix = "sub"
    noun = "subscription"

    def for_customer(self, customer_id):
        return [s for s in self.all() if s.customer == customer_id]

    def active(self):
        return [s for s in self.all() if s.status == "active"]


def create(app, customer_id, plan_id, start, quantity=1, anchor_day=1):
    """Start a subscription and issue its first invoice."""
    app.customers.get(customer_id)
    app.catalog.get(plan_id)
    if not isinstance(quantity, int) or not 1 <= quantity <= MAX_SEATS:
        raise ValidationError(f"quantity must be between 1 and {MAX_SEATS}", field="quantity")
    if not isinstance(anchor_day, int) or not 1 <= anchor_day <= 28:
        raise ValidationError("anchor_day must be between 1 and 28", field="anchor_day")
    sub = Subscription(app.subscriptions.next_id(), customer_id, plan_id, quantity, start, anchor_day)
    app.subscriptions.save(sub)
    invoicing.bill_signup(app, sub)
    app.events.emit("subscription.created", sub.id, customer=customer_id)
    return sub
