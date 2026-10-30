"""Everything the service can refuse to do. The text of the exception is the message shown to people."""


class BookingError(Exception):
    """Base class; str(error) is the human-readable reason."""


class NotFound(BookingError):
    """An id does not exist."""


class NotAllowed(BookingError):
    """The user's role does not permit this."""


class InvalidRequest(BookingError):
    """The request breaks a booking rule (time, size, state)."""


class Conflict(BookingError):
    """The room is taken at that time."""


class InsufficientBudget(BookingError):
    """The team cannot afford it."""
