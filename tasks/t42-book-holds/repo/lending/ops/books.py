from .. import validate
from ..models import Book
from ..views import book_view
from .registry import operation


@operation("book.create")
def create(svc, params):
    now = svc.clock.now()
    title = validate.require_str(params, "title")
    book = Book(id=svc.ids.new("book"), title=title, created_at=now, updated_at=now)
    svc.store.books[book.id] = book
    view = book_view(book)
    svc.bus.emit("book.created", {"book": view})
    return view


@operation("book.retrieve")
def retrieve(svc, params):
    return book_view(svc.store.get_book(validate.require_str(params, "book")))
