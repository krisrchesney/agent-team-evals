"""Error types raised by tracelens."""


class TracelensError(Exception):
    """Base class for every error this package raises on purpose."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


class ValidationError(TracelensError):
    """A value was missing or malformed."""


class NotFound(TracelensError):
    """A record id did not match anything."""


class Conflict(TracelensError):
    """The request is valid but not allowed in the current state."""
