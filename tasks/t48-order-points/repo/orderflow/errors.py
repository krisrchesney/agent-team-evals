class FlowError(Exception):
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param

    def as_dict(self):
        return {"code": self.code, "message": self.message, "param": self.param}


class InvalidRequest(FlowError):
    code = "invalid_request"


class NotFound(FlowError):
    code = "not_found"


class Conflict(FlowError):
    code = "conflict"


class UnknownOperation(FlowError):
    code = "unknown_operation"
