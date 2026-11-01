from datetime import datetime, timezone

from .errors import InvalidRequest

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
MAX_SHIFT_HOURS = 16


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


def shift_span(params):
    start = require_time(params, "start")
    end = require_time(params, "end")
    if end <= start:
        raise InvalidRequest("end must be after start", param="end")
    if (end - start).total_seconds() > MAX_SHIFT_HOURS * 3600:
        raise InvalidRequest(f"a shift is at most {MAX_SHIFT_HOURS} hours", param="end")
    return start, end


def limit(params, default=10, maximum=100):
    value = params.get("limit", default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise InvalidRequest(f"limit must be between 1 and {maximum}", param="limit")
    return value
