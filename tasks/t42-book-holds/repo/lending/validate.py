from .errors import InvalidRequest


def require_str(params, name):
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequest(f"{name} must be a non-empty string", param=name)
    return value.strip()
