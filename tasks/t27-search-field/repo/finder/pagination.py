"""Page arithmetic for result lists."""
from .errors import QueryError


def page_bounds(page, per_page, total):
    """(offset, limit, pages) for a 1-based page number."""
    if page < 1 or per_page < 1:
        raise QueryError("page and per_page must be at least 1", field="page")
    pages = max(1, -(-total // per_page))
    if page > pages:
        raise QueryError(f"page {page} is past the last page ({pages})", field="page")
    return (page - 1) * per_page, per_page, pages


def search_page(searcher, text, page=1, per_page=10, **options):
    """Run a search for one page; the result also tells how many pages there are."""
    first = searcher.search(text, limit=per_page, offset=0, **options)
    offset, limit, pages = page_bounds(page, per_page, first.total)
    result = first if offset == 0 else searcher.search(text, limit=limit, offset=offset, **options)
    return result, pages
