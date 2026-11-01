class LendingError(Exception):
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param

    def as_dict(self):
        return {"code": self.code, "message": self.message, "param": self.param}


class InvalidRequest(LendingError):
    code = "invalid_request"


class NotFound(LendingError):
    code = "not_found"


class Conflict(LendingError):
    code = "conflict"


class UnknownOperation(LendingError):
    code = "unknown_operation"
