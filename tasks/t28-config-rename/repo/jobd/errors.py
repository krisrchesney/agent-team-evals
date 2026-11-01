"""Error types raised by jobd."""


class JobdError(Exception):
    """Base class for every error this package raises on purpose."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


class ValidationError(JobdError):
    """A value was missing or malformed."""


class NotFound(JobdError):
    """A record id did not match anything."""


class Conflict(JobdError):
    """The request is valid but not allowed in the current state."""


class ConfigError(JobdError):
    """A setting is unknown, malformed or out of range."""
