class MeterError(Exception):
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param

    def as_dict(self):
        return {"code": self.code, "message": self.message, "param": self.param}


class InvalidRequest(MeterError):
    code = "invalid_request"


class NotFound(MeterError):
    code = "not_found"


class Conflict(MeterError):
    code = "conflict"


class UnknownOperation(MeterError):
    code = "unknown_operation"
