class RateLimitError(Exception):
    """Base class for this package's own errors. Bad arguments raise ValueError instead."""


class UnknownRule(RateLimitError):
    """A rule name that the limiter was not given."""


class StoreCorrupt(RateLimitError):
    """The persisted state could not be read."""
