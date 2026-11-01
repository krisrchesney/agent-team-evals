class ClinicError(Exception):
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param

    def as_dict(self):
        return {"code": self.code, "message": self.message, "param": self.param}


class InvalidRequest(ClinicError):
    code = "invalid_request"


class NotFound(ClinicError):
    code = "not_found"


class Conflict(ClinicError):
    code = "conflict"


class UnknownOperation(ClinicError):
    code = "unknown_operation"
