from . import exitcodes


class CliError(Exception):
    code = 1

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class UsageError(CliError):
    code = exitcodes.USAGE


class NotFound(CliError):
    code = exitcodes.NOT_FOUND


class IoFailure(CliError):
    code = exitcodes.IO


class Conflict(CliError):
    code = exitcodes.CONFLICT
