class DeskError(Exception):
    """Base class. `code` is stable and machine readable; `param` names the offending argument."""
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param


class InvalidInput(DeskError):
    code = "invalid_input"


class NotFound(DeskError):
    code = "not_found"


class Conflict(DeskError):
    code = "conflict"
