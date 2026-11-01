from datetime import timedelta

from .. import validate
from ..errors import Conflict, Unavailable
from ..models import Fine, Loan
from ..views import available, fine_view, loan_view, reservation_view
from . import reservations
from .registry import operation

LOAN_DAYS = 14
FINE_PER_DAY = 25  # cents for each started day late


def close(svc, loan, now):
    """Mark a loan returned and charge the fine if it is late. Returns the events to emit, in order."""
    loan.status = "returned"
    loan.returned_at = now
    svc.store.bump(loan, now)
    events = [("loan.returned", {"loan": loan_view(loan)})]
    if now > loan.due:
        days = -((loan.due - now) // timedelta(days=1))
        fine = Fine(id=svc.ids.new("fine"), loan=loan.id, member=loan.member,
                    amount=days * FINE_PER_DAY, created_at=now)
        svc.store.fines[fine.id] = fine
        events.append(("fine.charged", {"fine": fine_view(fine)}))
    events.extend(reservations.offer(svc, svc.store.get_book(loan.book), now))
    return events


@operation("loan.checkout")
def checkout(svc, params):
    now = svc.clock.now()
    book = svc.store.get_book(validate.require_str(params, "book"))
    member = svc.store.get_member(validate.require_str(params, "member"))
    if book.status != "active":
        raise Conflict(f"{book.title} is not in circulation", param="book")
    if member.status != "active":
        raise Conflict(f"{member.name} is suspended", param="member")
    ready = next(iter(r for r in svc.store.reservations_for(book.id, "ready") if r.member == member.id), None)
    if available(svc, book) + (1 if ready else 0) < 1:
        raise Unavailable(f"no copy of {book.title} is available", param="book")
    loan = Loan(id=svc.ids.new("loan"), book=book.id, member=member.id, status="open",
                due=now + timedelta(days=LOAN_DAYS), returned_at=None, created_at=now, updated_at=now)
    svc.store.loans[loan.id] = loan
    view = loan_view(loan)
    events = [("loan.created", {"loan": view})]
    if ready:
        ready.status = "fulfilled"
        svc.store.bump(ready, now)
        events.append(("reservation.fulfilled", {"reservation": reservation_view(ready)}))
    for type_, data in events:
        svc.bus.emit(type_, data)
    return view


@operation("loan.return")
def return_(svc, params):
    now = svc.clock.now()
    loan = svc.store.get_loan(validate.require_str(params, "loan"))
    if loan.status != "open":
        raise Conflict(f"loan {loan.id} is already returned", param="loan")
    events = close(svc, loan, now)
    for type_, data in events:
        svc.bus.emit(type_, data)
    return loan_view(loan)


@operation("loan.retrieve")
def retrieve(svc, params):
    return loan_view(svc.store.get_loan(validate.require_str(params, "loan")))


@operation("loan.fines")
def fines(svc, params):
    member = svc.store.get_member(validate.require_str(params, "member"))
    limit = validate.limit(params)
    rows = [f for _, f in sorted(svc.store.fines.items()) if f.member == member.id]
    return {"data": [fine_view(f) for f in rows[:limit]], "has_more": len(rows) > limit}
