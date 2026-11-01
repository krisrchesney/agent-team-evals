class CreditError(Exception):
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param

    def as_dict(self):
        return {"code": self.code, "message": self.message, "param": self.param}


class InvalidRequest(CreditError):
    code = "invalid_request"


class NotFound(CreditError):
    code = "not_found"


class Conflict(CreditError):
    code = "conflict"


class UnknownOperation(CreditError):
    code = "unknown_operation"
