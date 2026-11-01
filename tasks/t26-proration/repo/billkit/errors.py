"""Error types raised by billkit."""


class BillkitError(Exception):
    """Base class for every error this package raises on purpose."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


class ValidationError(BillkitError):
    """A value was missing or malformed."""


class NotFound(BillkitError):
    """A record id did not match anything."""


class Conflict(BillkitError):
    """The request is valid but not allowed in the current state."""
