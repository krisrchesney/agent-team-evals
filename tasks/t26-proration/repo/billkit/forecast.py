"""Cash forecast: what we expect to invoice over the next few periods."""
from datetime import date

from . import periods


def next_period_amounts(app, today):
    """Full-price amount each active subscription will be billed at its next renewal."""
    rows = []
    for sub in app.subscriptions.active():
        plan = app.catalog.get(sub.plan)
        _, end = periods.period_for(sub, max(today, sub.start), plan.interval)
        rows.append((end, sub.id, plan.price_cents * sub.quantity))
    return sorted(rows)


def expected_by_month(app, today, months):
    """Expected renewal revenue per calendar month, assuming nobody changes or cancels."""
    totals = {}
    for sub in app.subscriptions.active():
        plan = app.catalog.get(sub.plan)
        _, cursor = periods.period_for(sub, max(today, sub.start), plan.interval)
        for _ in range(months):
            key = (cursor.year, cursor.month)
            totals[key] = totals.get(key, 0) + plan.price_cents * sub.quantity
            cursor = periods.add_months(cursor, 12 if plan.interval == "year" else 1)
    horizon = periods.add_months(date(today.year, today.month, 1), months + 1)
    return {k: v for k, v in sorted(totals.items()) if date(k[0], k[1], 1) < horizon}
