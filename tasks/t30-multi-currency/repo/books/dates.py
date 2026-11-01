import calendar
from datetime import date

from .errors import InvalidDate


def parse(value, param="date"):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise InvalidDate(f"{param} must be an ISO date (YYYY-MM-DD)", param=param) from None


def month_bounds(month):
    """'2026-02' -> (date(2026, 2, 1), date(2026, 2, 28))."""
    try:
        year, mon = (int(part) for part in month.split("-"))
        last = calendar.monthrange(year, mon)[1]
        return date(year, mon, 1), date(year, mon, last)
    except (AttributeError, ValueError, calendar.IllegalMonthError):
        raise InvalidDate("month must look like 2026-02", param="month") from None


def add_months(d, months):
    index = d.year * 12 + d.month - 1 + months
    year, mon = divmod(index, 12)
    mon += 1
    return date(year, mon, min(d.day, calendar.monthrange(year, mon)[1]))
