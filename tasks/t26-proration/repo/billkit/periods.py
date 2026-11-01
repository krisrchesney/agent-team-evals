"""Billing periods. A period is [start, end): `end` is the first day of the next period.

Monthly subscriptions renew on `anchor_day` (1 to 28) of every month. Yearly subscriptions renew on
the anniversary of their start date.
"""
from datetime import date, timedelta

from .errors import ValidationError


def days_in_month(year, month):
    first = date(year, month, 1)
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    return (nxt - first).days


def add_months(d, months):
    """Move `d` by whole months, clamping the day to the length of the target month."""
    year, month0 = divmod(d.year * 12 + d.month - 1 + months, 12)
    month = month0 + 1
    return date(year, month, min(d.day, days_in_month(year, month)))


def month_period(anchor_day, on):
    start = date(on.year, on.month, anchor_day)
    if start > on:
        start = add_months(start, -1)
    return start, add_months(start, 1)


def year_period(first_day, on):
    years = on.year - first_day.year
    start = add_months(first_day, 12 * years)
    if start > on:
        years -= 1
        start = add_months(first_day, 12 * years)
    return start, add_months(first_day, 12 * (years + 1))


def period_for(sub, on, interval):
    """The billing period of `sub` that contains the day `on`."""
    if on < sub.start:
        raise ValidationError("date is before the subscription started", field="on")
    if interval == "year":
        return year_period(sub.start, on)
    return month_period(sub.anchor_day, on)


def days_between(a, b):
    return (b - a).days


def last_day(period):
    return period[1] - timedelta(days=1)
