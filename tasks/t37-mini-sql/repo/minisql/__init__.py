from .catalog import Catalog
from .engine import Result, execute
from .errors import CatalogError, ParseError, QueryError, SqlError
from .parser import parse


def query(sql, catalog):
    """Parse and run one SELECT statement. Returns a Result."""
    return execute(parse(sql), catalog)


__all__ = ["query", "parse", "execute", "Catalog", "Result", "SqlError", "ParseError", "QueryError", "CatalogError"]
