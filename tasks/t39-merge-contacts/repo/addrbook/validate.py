from .errors import InvalidRequest

KINDS = ("call", "email", "meeting")


def require_str(params, name):
    value = params.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequest(f"{name} must be a non-empty string", param=name)
    return value.strip()


def optional_str(params, name, default):
    if params.get(name) is None:
        return default
    return require_str(params, name)


def str_list(params, name, check=None):
    """A list of non-empty strings (stripped), absent means empty. `check` may veto one entry."""
    value = params.get(name)
    if value is None:
        return []
    if not isinstance(value, list):
        raise InvalidRequest(f"{name} must be a list", param=name)
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or (check and not check(item.strip())):
            raise InvalidRequest(f"{name} has an invalid entry {item!r}", param=name)
        out.append(item.strip())
    return out


def is_email(text):
    local, _, domain = text.partition("@")
    return bool(local) and "." in domain


def is_phone(text):
    return any(ch.isdigit() for ch in text)


def kind(params):
    value = params.get("kind")
    if value not in KINDS:
        raise InvalidRequest(f"kind must be one of {', '.join(KINDS)}", param="kind")
    return value


def limit(params, default=10, maximum=100):
    value = params.get("limit", default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise InvalidRequest(f"limit must be between 1 and {maximum}", param="limit")
    return value
