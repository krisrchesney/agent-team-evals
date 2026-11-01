class BookError(Exception):
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param

    def as_dict(self):
        return {"code": self.code, "message": self.message, "param": self.param}


class InvalidRequest(BookError):
    code = "invalid_request"


class NotFound(BookError):
    code = "not_found"


class Conflict(BookError):
    code = "conflict"


class UnknownOperation(BookError):
    code = "unknown_operation"
