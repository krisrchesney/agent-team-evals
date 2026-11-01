"""Parsing and formatting of times. Every datetime in sched is a naive wall-clock time."""
import re
from datetime import date, datetime, time, timedelta

from .errors import InvalidDuration, InvalidTime

_DT = re.compile(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(:\d{2})?$")
_DUR = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?$")


def parse_dt(value, param="start"):
    """'2026-03-02T09:00' (seconds allowed, then dropped) or a datetime -> naive datetime."""
    if isinstance(value, datetime):
        return value.replace(second=0, microsecond=0)
    match = _DT.match(value.strip()) if isinstance(value, str) else None
    if not match:
        raise InvalidTime(f"{param} must look like 2026-03-02T09:00", param=param)
    try:
        return datetime.fromisoformat(f"{match.group(1)}T{match.group(2)}")
    except ValueError:
        raise InvalidTime(f"{param} is not a real date and time", param=param) from None


def parse_date(value, param="day"):
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise InvalidTime(f"{param} must look like 2026-03-02", param=param) from None


def parse_time(value, param="time"):
    try:
        hour, minute = (int(part) for part in value.split(":"))
        return time(hour, minute)
    except (AttributeError, ValueError):
        raise InvalidTime(f"{param} must look like 09:00", param=param) from None


def parse_duration(value, param="duration"):
    """'90m', '2h', '1h30m' or a whole number of minutes -> timedelta (at most 24 hours)."""
    if isinstance(value, bool):
        raise InvalidDuration("duration must be text like 1h30m or a number of minutes", param=param)
    if isinstance(value, int):
        minutes = value
    else:
        match = _DUR.match(value.strip()) if isinstance(value, str) else None
        if not match or not (match.group(1) or match.group(2)):
            raise InvalidDuration("duration must be text like 1h30m or a number of minutes", param=param)
        minutes = int(match.group(1) or 0) * 60 + int(match.group(2) or 0)
    if not 1 <= minutes <= 24 * 60:
        raise InvalidDuration("duration must be between 1 minute and 24 hours", param=param)
    return timedelta(minutes=minutes)


def fmt_dt(dt):
    """Naive datetime -> '2026-03-02T09:00'."""
    return dt.strftime("%Y-%m-%dT%H:%M")


def fmt_clock(dt):
    return dt.strftime("%H:%M")


def fmt_time(t):
    return t.strftime("%H:%M")


def fmt_duration(delta):
    minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    return (f"{hours}h" if hours else "") + (f"{minutes}m" if minutes else "")
