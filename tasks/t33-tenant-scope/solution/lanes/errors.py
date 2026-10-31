class LaneError(Exception):
    """Base class. `code` is stable and machine readable; `param` names the offending argument."""
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param


class InvalidInput(LaneError):
    code = "invalid_input"


class NotFound(LaneError):
    code = "not_found"


class Conflict(LaneError):
    code = "conflict"


class QuotaExceeded(LaneError):
    code = "quota_exceeded"


class RateLimited(LaneError):
    code = "rate_limited"


class UnknownTenant(LaneError):
    code = "unknown_tenant"
