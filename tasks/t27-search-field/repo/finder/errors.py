"""Error types raised by finder."""


class FinderError(Exception):
    """Base class for every error this package raises on purpose."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


class ValidationError(FinderError):
    """A value was missing or malformed."""


class NotFound(FinderError):
    """A record id did not match anything."""


class Conflict(FinderError):
    """The request is valid but not allowed in the current state."""


class QueryError(FinderError):
    """A query or search option could not be understood."""
