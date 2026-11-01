class BillError(Exception):
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param

    def as_dict(self):
        return {"code": self.code, "message": self.message, "param": self.param}


class InvalidRequest(BillError):
    code = "invalid_request"


class NotFound(BillError):
    code = "not_found"


class Conflict(BillError):
    code = "conflict"


class UnknownOperation(BillError):
    code = "unknown_operation"
