from datetime import datetime

from .errors import UsageError


def parse_date(text, what):
    """A calendar date such as 2026-03-31. Anything else is a usage error naming `what`."""
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise UsageError(f"{what} must be a date like 2026-03-31, not {text!r}") from None


def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
