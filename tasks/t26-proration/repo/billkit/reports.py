"""Reports over the books."""
from collections import defaultdict
from decimal import Decimal

from .constants import AGING_BUCKETS
from .dunning import days_overdue
from .money import round_cents


def aging_report(app, today):
    """Unpaid invoices grouped by how many days past due they are (30/60/90 day buckets)."""
    labels = [f"<={b}" for b in AGING_BUCKETS] + [f">{AGING_BUCKETS[-1]}"]
    totals = {label: 0 for label in labels}
    for invoice in app.invoices.unpaid():
        late = days_overdue(invoice, today)
        if late == 0:
            continue
        for bound, label in zip(AGING_BUCKETS, labels):
            if late <= bound:
                totals[label] += invoice.total_cents
                break
        else:
            totals[labels[-1]] += invoice.total_cents
    return totals


def mrr_cents(app):
    """Monthly recurring revenue of active subscriptions; yearly plans count one twelfth."""
    total = Decimal(0)
    for sub in app.subscriptions.active():
        plan = app.catalog.get(sub.plan)
        price = Decimal(plan.price_cents * sub.quantity)
        total += price if plan.interval == "month" else price / 12
    return round_cents(total)


def revenue_by_plan(app):
    out = defaultdict(int)
    for sub in app.subscriptions.active():
        plan = app.catalog.get(sub.plan)
        out[plan.id] += plan.price_cents * sub.quantity
    return dict(out)


def customers_by_region(app):
    out = defaultdict(list)
    for customer in app.customers.all():
        out[customer.region or "unknown"].append(customer.id)
    return {k: sorted(v) for k, v in out.items()}


def churn(app, since, until):
    """Subscriptions canceled in [since, until) as a share of those active at `since`."""
    started = [s for s in app.subscriptions.all() if s.start < since]
    if not started:
        return Decimal(0)
    live_at_since = [s for s in started if s.canceled_on is None or s.canceled_on >= since]
    canceled = [s for s in live_at_since if s.canceled_on is not None and s.canceled_on < until]
    return Decimal(len(canceled)) / Decimal(len(live_at_since)) if live_at_since else Decimal(0)
