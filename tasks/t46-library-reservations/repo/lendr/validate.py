from .errors import InvalidRequest

MAX_COPIES = 50


def require_str(params, name):
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequest(f"{name} must be a non-empty string", param=name)
    return value.strip()


def require_copies(params, name="copies"):
    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidRequest(f"{name} must be a whole number", param=name)
    if not 1 <= value <= MAX_COPIES:
        raise InvalidRequest(f"{name} must be between 1 and {MAX_COPIES}", param=name)
    return value


def limit(params, default=10, maximum=100):
    value = params.get("limit", default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise InvalidRequest(f"limit must be between 1 and {maximum}", param="limit")
    return value
