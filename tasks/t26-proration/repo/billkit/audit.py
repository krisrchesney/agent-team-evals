"""Summaries of the event log for support staff."""
from collections import Counter


def counts_by_kind(app):
    return dict(sorted(Counter(e["kind"] for e in app.events.entries).items()))


def timeline(app, subject):
    """Human-readable lines for everything that happened to one subscription or invoice."""
    out = []
    for n, entry in enumerate(app.events.for_subject(subject), start=1):
        extras = ", ".join(f"{k}={v}" for k, v in entry.items() if k not in ("kind", "subject"))
        out.append(f"{n}. {entry['kind']}" + (f" ({extras})" if extras else ""))
    return out


def customer_history(app, customer_id):
    """Invoices, credit notes and subscription events for one customer, oldest first."""
    rows = []
    for inv in app.invoices.for_customer(customer_id):
        rows.append((inv.issued_on.isoformat(), inv.kind, inv.id, inv.total_cents))
    for sub in app.subscriptions.for_customer(customer_id):
        rows.append((sub.start.isoformat(), "subscription", sub.id, 0))
        if sub.canceled_on:
            rows.append((sub.canceled_on.isoformat(), "canceled", sub.id, 0))
    return sorted(rows)


def busiest_customers(app, limit=5):
    totals = Counter()
    for inv in app.invoices.all():
        totals[inv.customer] += 1
    return totals.most_common(limit)
