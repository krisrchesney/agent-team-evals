"""Renewal runs: find subscriptions whose next period starts today and bill them."""
from datetime import timedelta

from . import invoicing, periods


def due_for_renewal(app, today):
    """Active subscriptions whose current period began today (and that were not billed for it yet)."""
    due = []
    for sub in app.subscriptions.active():
        if today <= sub.start:
            continue
        plan = app.catalog.get(sub.plan)
        start, _ = periods.period_for(sub, today, plan.interval)
        if start != today:
            continue
        already = [i for i in app.invoices.for_subscription(sub.id)
                   if i.kind == "invoice" and any(line.period_start == today for line in i.lines)]
        if not already:
            due.append(sub)
    return due


def run_renewals(app, today):
    """Bill every due subscription once. Returns the invoices that were issued."""
    issued = []
    for sub in due_for_renewal(app, today):
        issued.append(invoicing.bill_renewal(app, sub, today))
    return issued


def upcoming(app, today, days):
    """(date, subscription id) pairs for renewals in the next `days` days, soonest first."""
    rows = []
    for offset in range(1, days + 1):
        day = today + timedelta(days=offset)
        for sub in due_for_renewal(app, day):
            rows.append((day, sub.id))
    return rows
