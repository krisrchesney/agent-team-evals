class SchedError(Exception):
    """Base class. `code` is stable and machine readable; `param` names the offending argument."""
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param


class InvalidTime(SchedError):
    code = "invalid_time"


class InvalidZone(SchedError):
    code = "invalid_zone"


class InvalidDuration(SchedError):
    code = "invalid_duration"


class InvalidRule(SchedError):
    code = "invalid_rule"


class UnknownUser(SchedError):
    code = "unknown_user"


class DuplicateUser(SchedError):
    code = "duplicate_user"


class UnknownCalendar(SchedError):
    code = "unknown_calendar"


class UnknownEvent(SchedError):
    code = "unknown_event"


class Conflict(SchedError):
    code = "conflict"
