from datetime import datetime, timezone

from .errors import FlagConfigError

_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def parse_time(flag, field, value):
    """Parse a UTC time such as 2026-03-02T09:00:00Z. Anything else is a config error on `field`."""
    if not isinstance(value, str):
        raise FlagConfigError(flag, field, "must be a time like 2026-03-02T09:00:00Z")
    try:
        return datetime.strptime(value, _FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        raise FlagConfigError(flag, field, f"{value!r} is not a time like 2026-03-02T09:00:00Z") from None


def format_time(dt):
    return dt.strftime(_FORMAT)
