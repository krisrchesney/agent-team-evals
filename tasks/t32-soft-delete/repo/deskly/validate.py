import re

from .errors import InvalidInput

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TAG = re.compile(r"^[a-z0-9-]{1,20}$")
STATUSES = ("open", "pending", "closed")
MAX_TAGS = 5


def text(value, name, max_len=200):
    if not isinstance(value, str) or not value.strip():
        raise InvalidInput(f"{name} must be a non-empty string", param=name)
    value = value.strip()
    if len(value) > max_len:
        raise InvalidInput(f"{name} must be at most {max_len} characters", param=name)
    return value


def email(value):
    value = text(value, "email").lower()
    if not EMAIL.match(value):
        raise InvalidInput("email is not valid", param="email")
    return value


def priority(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 3:
        raise InvalidInput("priority must be 1, 2 or 3", param="priority")
    return value


def status(value):
    if value not in STATUSES:
        raise InvalidInput(f"status must be one of {', '.join(STATUSES)}", param="status")
    return value


def tag(value):
    value = text(value, "tag").lower()
    if not TAG.match(value):
        raise InvalidInput("a tag is 1 to 20 letters, digits or dashes", param="tag")
    return value


def tags(values):
    found = sorted({tag(v) for v in values})
    if len(found) > MAX_TAGS:
        raise InvalidInput(f"a ticket has at most {MAX_TAGS} tags", param="tags")
    return tuple(found)


def limit(value, default=10, maximum=100):
    value = default if value is None else value
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise InvalidInput(f"limit must be between 1 and {maximum}", param="limit")
    return value
