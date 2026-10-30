"""Date helpers. Dates in the input are ISO `YYYY-MM-DD` and nothing else."""
import re
from datetime import date

_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def parse_iso(text):
    """'2024-03-09' -> date(2024, 3, 9). Raises ValueError for any other shape or a bad calendar date."""
    m = _ISO.match(text)
    if not m:
        raise ValueError(text)
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def month_key(day):
    """The calendar month of `day` as a sortable number: 2024-03 -> 202403."""
    return day.year * 100 + day.month


def days_between(first, last):
    """Whole days from `first` to `last` (negative if `last` is earlier)."""
    return (last - first).days


def is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
