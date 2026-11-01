"""lendr: books, members and loans for a small lending library.

    from lendr import Service
    svc = Service()
    book = svc.call("book.create", title="Dune", copies=2)
    member = svc.call("member.create", name="Ada")
    svc.call("loan.checkout", book=book["id"], member=member["id"])
"""
from .service import Service

__all__ = ["Service"]
