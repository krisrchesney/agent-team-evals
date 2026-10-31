class SqlError(Exception):
    """Base class of every error raised for a bad query or bad data."""


class ParseError(SqlError):
    """Bad syntax. `pos` is the 0-based character offset in the SQL text where the problem is."""

    def __init__(self, message, pos):
        super().__init__("%s (at %d)" % (message, pos))
        self.pos = pos


class QueryError(SqlError):
    """The SQL parses but cannot be run (unknown column, type mismatch, bad grouping, ...)."""


class CatalogError(SqlError):
    """A table is missing or its CSV file is malformed."""
