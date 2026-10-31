from .errors import InvalidRequest

MAX_QUANTITY = 10_000


def require_str(params, name):
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequest(f"{name} must be a non-empty string", param=name)
    return value.strip()


def optional_str(params, name, default):
    if params.get(name) is None:
        return default
    return require_str(params, name)


def require_qty(params, name="quantity"):
    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidRequest(f"{name} must be a whole number", param=name)
    if not 1 <= value <= MAX_QUANTITY:
        raise InvalidRequest(f"{name} must be between 1 and {MAX_QUANTITY}", param=name)
    return value


def require_delta(params, name="delta"):
    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value == 0:
        raise InvalidRequest(f"{name} must be a non-zero whole number", param=name)
    if abs(value) > MAX_QUANTITY:
        raise InvalidRequest(f"{name} must be at most {MAX_QUANTITY} either way", param=name)
    return value


def limit(params, default=10, maximum=100):
    value = params.get("limit", default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise InvalidRequest(f"limit must be between 1 and {maximum}", param="limit")
    return value
