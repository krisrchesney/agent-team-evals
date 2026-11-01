from datetime import datetime, timedelta, timezone

from .errors import InvalidRequest

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
MAX_MINUTES = 240


def require_str(params, name):
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequest(f"{name} must be a non-empty string", param=name)
    return value.strip()


def require_time(params, name):
    text = require_str(params, name)
    try:
        return datetime.strptime(text, TIME_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        raise InvalidRequest(f"{name} must look like 2026-01-12T09:00:00Z", param=name) from None


def appointment_span(params, now):
    """(start, end) of a slot: it must begin after `now` and last 1 to MAX_MINUTES minutes."""
    start = require_time(params, "start")
    minutes = params.get("minutes")
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= MAX_MINUTES:
        raise InvalidRequest(f"minutes must be a whole number from 1 to {MAX_MINUTES}", param="minutes")
    if start <= now:
        raise InvalidRequest("start must be in the future", param="start")
    return start, start + timedelta(minutes=minutes)


def limit(params, default=10, maximum=100):
    value = params.get("limit", default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise InvalidRequest(f"limit must be between 1 and {maximum}", param="limit")
    return value
