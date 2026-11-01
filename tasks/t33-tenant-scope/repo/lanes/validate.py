import re
from datetime import date

from .errors import InvalidInput

STATUSES = ("todo", "doing", "done")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LABEL = re.compile(r"^[a-z0-9-]{1,20}$")
COLOR = re.compile(r"^#[0-9a-f]{6}$")


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


def status(value):
    if value not in STATUSES:
        raise InvalidInput(f"status must be one of {', '.join(STATUSES)}", param="status")
    return value


def priority(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 3:
        raise InvalidInput("priority must be 1, 2 or 3", param="priority")
    return value


def due(value):
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise InvalidInput("due must look like 2026-03-31", param="due") from None


def label_name(value):
    value = text(value, "name").lower()
    if not LABEL.match(value):
        raise InvalidInput("a label is 1 to 20 letters, digits or dashes", param="name")
    return value


def color(value):
    value = text(value, "color").lower()
    if not COLOR.match(value):
        raise InvalidInput("color must look like #aabbcc", param="color")
    return value


def limit(value, default=20, maximum=100):
    value = default if value is None else value
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise InvalidInput(f"limit must be between 1 and {maximum}", param="limit")
    return value
