from .. import validate
from ..models import Book
from ..views import book_view
from . import loans
from .registry import operation


@operation("book.create")
def create(svc, params):
    now = svc.clock.now()
    title = validate.require_str(params, "title")
    copies = validate.require_copies(params)
    book = Book(id=svc.ids.new("book"), title=title, copies=copies, status="active",
                created_at=now, updated_at=now)
    svc.store.books[book.id] = book
    view = book_view(svc, book)
    svc.bus.emit("book.created", {"book": view})
    return view


@operation("book.retrieve")
def retrieve(svc, params):
    return book_view(svc, svc.store.get_book(validate.require_str(params, "book")))


@operation("book.list")
def list_books(svc, params):
    limit = validate.limit(params)
    books = sorted(svc.store.books.values(), key=lambda b: (b.created_at, b.id))
    return {"data": [book_view(svc, b) for b in books[:limit]], "has_more": len(books) > limit}


@operation("book.retire")
def retire(svc, params):
    """Take a book out of circulation; copies still out are counted as returned."""
    now = svc.clock.now()
    book = svc.store.get_book(validate.require_str(params, "book"))
    book.status = "retired"
    svc.store.bump(book, now)
    events = []
    for loan in svc.store.open_loans(book_id=book.id):
        events.extend(loans.close(svc, loan, now))
    view = book_view(svc, book)
    svc.bus.emit("book.retired", {"book": view})
    for type_, data in events:
        svc.bus.emit(type_, data)
    return view
