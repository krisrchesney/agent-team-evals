from datetime import datetime

from .errors import InvalidRequest

MAX_AMOUNT = 100_000_000


def require_str(params, name):
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequest(f"{name} must be a non-empty string", param=name)
    return value.strip()


def optional_str(params, name, default):
    if params.get(name) is None:
        return default
    return require_str(params, name)


def require_amount(params, name="amount"):
    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidRequest(f"{name} must be a whole number of cents", param=name)
    if not 1 <= value <= MAX_AMOUNT:
        raise InvalidRequest(f"{name} must be between 1 and {MAX_AMOUNT} cents", param=name)
    return value


def require_date(params, name):
    text = require_str(params, name)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise InvalidRequest(f"{name} must look like 2026-02-01", param=name) from None


def limit(params, default=10, maximum=100):
    value = params.get("limit", default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise InvalidRequest(f"limit must be between 1 and {maximum}", param="limit")
    return value
