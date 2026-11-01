class LendrError(Exception):
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param

    def as_dict(self):
        return {"code": self.code, "message": self.message, "param": self.param}


class InvalidRequest(LendrError):
    code = "invalid_request"


class NotFound(LendrError):
    code = "not_found"


class Conflict(LendrError):
    code = "conflict"


class Unavailable(Conflict):
    code = "unavailable"


class UnknownOperation(LendrError):
    code = "unknown_operation"
