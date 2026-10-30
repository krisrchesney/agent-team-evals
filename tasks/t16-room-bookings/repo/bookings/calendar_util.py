"""Weekday names and day counting, independent of the machine's locale."""
from datetime import timedelta

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def weekdays_between(first, last):
    """Number of Monday-to-Friday days from `first` to `last`, both included (dates)."""
    count, day = 0, first
    while day <= last:
        if day.weekday() < 5:
            count += 1
        day += timedelta(days=1)
    return count
