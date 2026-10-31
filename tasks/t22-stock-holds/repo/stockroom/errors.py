class StockError(Exception):
    code = "error"

    def __init__(self, message, param=None):
        super().__init__(message)
        self.message = message
        self.param = param

    def as_dict(self):
        return {"code": self.code, "message": self.message, "param": self.param}


class InvalidRequest(StockError):
    code = "invalid_request"


class NotFound(StockError):
    code = "not_found"


class Conflict(StockError):
    code = "conflict"


class InsufficientStock(Conflict):
    code = "insufficient_stock"


class UnknownOperation(StockError):
    code = "unknown_operation"
