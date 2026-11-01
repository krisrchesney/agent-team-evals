"""Parsing and formatting of times.

Inside sched every datetime is aware and in UTC. A local wall-clock time becomes an instant through
`localize`; an instant becomes local text through `fmt_dt` and `fmt_clock`.
"""
import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .errors import InvalidDuration, InvalidTime, InvalidZone

UTC = timezone.utc
_DT = re.compile(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(:\d{2})?(Z|[+-]\d{2}:\d{2})?$")
_DUR = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?$")


def get_zone(name, param="tz"):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError, OSError):
        raise InvalidZone(f"unknown time zone {name!r}", param=param) from None


def localize(naive, zone):
    """A local wall-clock time in `zone` -> the UTC instant.

    A time skipped by a clock change moves forward by the length of the gap; a time that happens
    twice is the first one.
    """
    return naive.replace(tzinfo=zone).astimezone(UTC)


def parse_dt(value, zone, param="start"):
    """Text or datetime -> aware UTC datetime. Text without an offset is local time in `zone`.

    Accepts '2026-03-02T09:00', with optional seconds (dropped) and an optional 'Z' or '+01:00'.
    """
    if isinstance(value, datetime):
        value = value.replace(second=0, microsecond=0)
        return value.astimezone(UTC) if value.tzinfo else localize(value, zone)
    match = _DT.match(value.strip()) if isinstance(value, str) else None
    if not match:
        raise InvalidTime(f"{param} must look like 2026-03-02T09:00", param=param)
    try:
        naive = datetime.fromisoformat(f"{match.group(1)}T{match.group(2)}")
        if match.group(4) is None:
            return localize(naive, zone)
        if match.group(4) == "Z":
            return naive.replace(tzinfo=UTC)
        sign = 1 if match.group(4)[0] == "+" else -1
        hours, minutes = int(match.group(4)[1:3]), int(match.group(4)[4:6])
        return naive.replace(tzinfo=timezone(sign * timedelta(hours=hours, minutes=minutes))).astimezone(UTC)
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


def fmt_dt(dt, zone):
    """Instant -> local ISO text with the offset, e.g. '2026-03-08T09:00-04:00'."""
    return dt.astimezone(zone).isoformat(timespec="minutes")


def fmt_clock(dt, zone):
    return dt.astimezone(zone).strftime("%H:%M")


def fmt_time(t):
    return t.strftime("%H:%M")


def fmt_utc(dt):
    """Instant -> '2026-03-08T14:00Z', the form snapshots store."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")


def fmt_duration(delta):
    minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    return (f"{hours}h" if hours else "") + (f"{minutes}m" if minutes else "")
