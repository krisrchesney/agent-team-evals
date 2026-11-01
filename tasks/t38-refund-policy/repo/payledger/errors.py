class LedgerError(Exception):
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param

    def as_dict(self):
        return {"code": self.code, "message": self.message, "param": self.param}


class InvalidRequest(LedgerError):
    code = "invalid_request"


class NotFound(LedgerError):
    code = "not_found"


class Conflict(LedgerError):
    code = "conflict"


class UnknownOperation(LedgerError):
    code = "unknown_operation"
