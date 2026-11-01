from .errors import InvalidRequest

MAX_QUANTITY = 1_000_000


def require_str(params, name):
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequest(f"{name} must be a non-empty string", param=name)
    return value.strip()


def require_qty(params, name="quantity"):
    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidRequest(f"{name} must be a whole number", param=name)
    if not 1 <= value <= MAX_QUANTITY:
        raise InvalidRequest(f"{name} must be between 1 and {MAX_QUANTITY}", param=name)
    return value
