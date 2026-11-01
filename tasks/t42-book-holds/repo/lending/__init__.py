"""lending: members, books and loans for a small community library. Times are UTC, written like 2026-01-12T09:00:00Z.

    from lending import Service
    svc = Service()
    ann = svc.call("member.create", name="Ann")
    dune = svc.call("book.create", title="Dune")
    svc.call("loan.borrow", book=dune["id"], member=ann["id"])
"""
from .service import Service

__all__ = ["Service"]
