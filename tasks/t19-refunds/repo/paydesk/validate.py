"""Parameter checks shared by all operations. See docs/ERRORS.md for the codes."""
from .errors import InvalidRequest


def check_id(value, param):
    """A non-empty str id. Returns it."""
    if not isinstance(value, str) or not value:
        raise InvalidRequest(f"{param} must be a non-empty string", code="invalid_param", param=param)
    return value


def check_choice(value, choices, param, code):
    if value not in choices:
        allowed = ", ".join(sorted(choices))
        raise InvalidRequest(f"{param} must be one of: {allowed}", code=code, param=param)
    return value
