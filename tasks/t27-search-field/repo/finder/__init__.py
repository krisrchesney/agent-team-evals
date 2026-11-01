"""finder: a small full-text search library."""
from .documents import Document, make
from .library import Library
from .search import Searcher

__all__ = ["Document", "Library", "Searcher", "make"]
