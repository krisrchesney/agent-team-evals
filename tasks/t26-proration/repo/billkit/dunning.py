"""Dunning: when to retry or chase an unpaid invoice."""
from datetime import timedelta

from .constants import DUNNING_DELAYS


def retry_dates(invoice):
    """The days on which we retry the card after an invoice falls due."""
    return [invoice.due_on + timedelta(days=d) for d in DUNNING_DELAYS]


def next_retry(invoice, today):
    for day in retry_dates(invoice):
        if day >= today:
            return day
    return None


def days_overdue(invoice, today):
    return max(0, (today - invoice.due_on).days)


def overdue_bucket(days):
    """Label used by collections: how late is this invoice?"""
    if days <= 0:
        return "current"
    if days <= 30:
        return "1-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    return "90+"


def should_suspend(invoice, today):
    """Suspend the subscription once an invoice is more than 30 days overdue."""
    return days_overdue(invoice, today) > 30


def collection_queue(app, today):
    rows = []
    for invoice in app.invoices.unpaid():
        late = days_overdue(invoice, today)
        if late:
            rows.append((late, invoice.id, overdue_bucket(late)))
    rows.sort(reverse=True)
    return rows
