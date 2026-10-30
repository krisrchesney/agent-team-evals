"""Errors the command line reports as `salesrep: error: ...`."""


class ParseError(ValueError):
    """The input file as a whole cannot be read (for example a required column is missing)."""


class UsageError(ValueError):
    """The command line options are wrong."""
