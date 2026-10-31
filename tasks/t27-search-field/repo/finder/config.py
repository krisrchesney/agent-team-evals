"""Settings for a Library, read from a plain dict (usually parsed JSON)."""
from dataclasses import dataclass

from .errors import ValidationError


@dataclass(frozen=True)
class Settings:
    cache_size: int = 128
    default_limit: int = 10
    max_limit: int = 100
    log_queries: bool = True
    suggest: bool = True


def load(data=None):
    data = dict(data or {})
    known = set(Settings.__dataclass_fields__)
    for key in data:
        if key not in known:
            raise ValidationError(f"unknown setting {key!r}", field=key)
    settings = Settings(**data)
    for name in ("cache_size", "default_limit", "max_limit"):
        value = getattr(settings, name)
        if not isinstance(value, int) or value < 1:
            raise ValidationError(f"{name} must be a positive whole number", field=name)
    if settings.default_limit > settings.max_limit:
        raise ValidationError("default_limit cannot be larger than max_limit", field="default_limit")
    return settings
