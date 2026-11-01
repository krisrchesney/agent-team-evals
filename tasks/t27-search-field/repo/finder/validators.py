"""Field checks shared by every entity module."""
import re

from .errors import ValidationError

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def text(data, name, required=True, limit=80):
    value = data.get(name, "")
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string", field=name)
    value = value.strip()
    if required and not value:
        raise ValidationError(f"{name} is required", field=name)
    if len(value) > limit:
        raise ValidationError(f"{name} is longer than {limit} characters", field=name)
    return value


def email(data, name):
    value = text(data, name, required=True, limit=120)
    if not _EMAIL.match(value):
        raise ValidationError(f"{name} is not an email address", field=name)
    return value.lower()


def integer(data, name, low, high):
    value = data.get(name, low)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{name} must be a whole number", field=name)
    if not low <= value <= high:
        raise ValidationError(f"{name} must be between {low} and {high}", field=name)
    return value


def choice(data, name, allowed, default):
    value = data.get(name, default)
    if value not in allowed:
        raise ValidationError(f"{name} must be one of {', '.join(allowed)}", field=name)
    return value
