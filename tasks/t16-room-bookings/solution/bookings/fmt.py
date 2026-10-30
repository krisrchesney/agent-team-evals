"""How money and time slots are written in messages and reports."""
from .calendar_util import MONTHS, WEEKDAYS


def money(cents):
    """1250 -> '$12.50', 123456 -> '$1,234.56'."""
    return f"${cents // 100:,}.{cents % 100:02d}"


def slot(start, end):
    """'Mon 03 Jun 09:00-10:30'."""
    day = f"{WEEKDAYS[start.weekday()]} {start.day:02d} {MONTHS[start.month - 1]}"
    return f"{day} {start:%H:%M}-{end:%H:%M}"
