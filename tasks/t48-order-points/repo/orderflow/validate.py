from .errors import InvalidRequest

MAX_TOTAL = 10_000_000  # cents


def require_str(params, name):
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequest(f"{name} must be a non-empty string", param=name)
    return value.strip()


def require_total(params, name="total"):
    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidRequest(f"{name} must be a whole number of cents", param=name)
    if not 1 <= value <= MAX_TOTAL:
        raise InvalidRequest(f"{name} must be between 1 and {MAX_TOTAL}", param=name)
    return value


def limit(params, default=10, maximum=100):
    value = params.get("limit", default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise InvalidRequest(f"limit must be between 1 and {maximum}", param="limit")
    return value
