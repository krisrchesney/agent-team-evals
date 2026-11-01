from datetime import datetime

from .errors import InvalidRequest

DATE_FORMAT = "%Y-%m-%d"


def require_str(params, name):
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequest(f"{name} must be a non-empty string", param=name)
    return value.strip()


def cents(params, name):
    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InvalidRequest(f"{name} must be a positive whole number of cents", param=name)
    return value


def require_date(params, name):
    text = require_str(params, name)
    try:
        return datetime.strptime(text, DATE_FORMAT).date()
    except ValueError:
        raise InvalidRequest(f"{name} must look like 2026-01-02", param=name) from None


def limit(params, default=10, maximum=100):
    value = params.get("limit", default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise InvalidRequest(f"limit must be between 1 and {maximum}", param="limit")
    return value
