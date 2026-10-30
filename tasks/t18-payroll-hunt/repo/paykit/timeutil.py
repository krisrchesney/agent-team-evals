"""Parsing of the clock times and calendar days that appear in timesheets."""
import datetime
import re

_TIME = re.compile(r"(\d{2}):(\d{2})")
_DAY = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

MINUTES_PER_DAY = 24 * 60


def parse_hhmm(text):
    """Turn a 24-hour 'HH:MM' string into minutes since midnight."""
    match = _TIME.fullmatch(text) if isinstance(text, str) else None
    if match is None:
        raise ValueError(f"bad time {text!r}: expected HH:MM")
    hours, minutes = int(match.group(1)), int(match.group(2))
    if hours > 23 or minutes > 59:
        raise ValueError(f"bad time {text!r}: out of range")
    return hours * 60 + minutes


def parse_day(text):
    """Turn a 'YYYY-MM-DD' string into a date. A date is returned unchanged."""
    if isinstance(text, datetime.date):
        return text
    match = _DAY.fullmatch(text) if isinstance(text, str) else None
    if match is None:
        raise ValueError(f"bad day {text!r}: expected YYYY-MM-DD")
    try:
        return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        raise ValueError(f"bad day {text!r}: no such date") from None
