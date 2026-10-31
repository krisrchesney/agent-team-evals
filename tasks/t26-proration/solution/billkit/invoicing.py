"""Invoices that come from a subscription starting or renewing."""
from . import periods
from .invoices import Line


def bill_signup(app, sub):
    """Issue the first invoice. A monthly plan that starts mid-cycle pays for the days left in the cycle."""
    plan = app.catalog.get(sub.plan)
    start, end = periods.period_for(sub, sub.start, plan.interval)
    if plan.interval == "month" and sub.start > start:
        stub_days = (end - sub.start).days
        amount = plan.price_cents * sub.quantity * stub_days // (end - start).days
        text = f"{plan.name}, {sub.start:%d %b} to {end:%d %b}"
        line = Line(text, amount, sub.start, end, "proration")
    else:
        line = Line(plan.name, plan.price_cents * sub.quantity, start, end, "subscription")
    return app.invoices.issue(app, sub.customer, sub.id, [line], sub.start)


def bill_renewal(app, sub, on):
    """Issue the invoice for the period that contains `on` (full price, no proration)."""
    plan = app.catalog.get(sub.plan)
    start, end = periods.period_for(sub, on, plan.interval)
    line = Line(plan.name, plan.price_cents * sub.quantity, start, end, "subscription")
    return app.invoices.issue(app, sub.customer, sub.id, [line], on)
