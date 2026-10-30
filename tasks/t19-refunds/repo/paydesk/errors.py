"""Error classes. Codes and when to use them: docs/ERRORS.md."""


class PaydeskError(Exception):
    code = "error"

    def __init__(self, message, *, code=None, param=None):
        super().__init__(message)
        if code is not None:
            self.code = code
        self.param = param

    def to_dict(self):
        return {"type": type(self).__name__, "code": self.code, "param": self.param, "message": str(self)}


class InvalidRequest(PaydeskError):
    code = "invalid_request"


class NotFound(PaydeskError):
    code = "not_found"


class Forbidden(PaydeskError):
    code = "forbidden"


class Conflict(PaydeskError):
    code = "conflict"
