"""Included usage (units per period) that comes with a plan."""
from . import periods


def allowance(app, sub_id, on):
    """Units included in the period containing `on`. The first, partial period gets a share of them."""
    sub = app.subscriptions.get(sub_id)
    plan = app.catalog.get(sub.plan)
    full = plan.included_units * sub.quantity
    start, end = periods.period_for(sub, on, plan.interval)
    first = periods.period_for(sub, sub.start, plan.interval)
    if (start, end) == first and plan.interval == "month" and sub.start > start:
        stub_days = (end - sub.start).days
        return full * stub_days // (end - start).days
    return full


def overage_units(app, sub_id, on, used):
    return max(0, used - allowance(app, sub_id, on))
