from datetime import timedelta

from .. import validate
from ..errors import Conflict
from ..models import Reservation
from ..views import available, reservation_view
from .registry import operation

PICKUP_DAYS = 3


def offer(svc, book, now):
    """Hold a free copy for the first member waiting for it. Returns the events to emit, in order."""
    if book.status != "active" or available(svc, book) < 1:
        return []
    waiting = svc.store.reservations_for(book.id, "waiting")
    if not waiting:
        return []
    first = waiting[0]
    first.status = "ready"
    first.pickup_by = now + timedelta(days=PICKUP_DAYS)
    svc.store.bump(first, now)
    return [("reservation.ready", {"reservation": reservation_view(first)})]


@operation("reservation.create")
def place(svc, params):
    now = svc.clock.now()
    book = svc.store.get_book(validate.require_str(params, "book"))
    member = svc.store.get_member(validate.require_str(params, "member"))
    if book.status != "active":
        raise Conflict(f"{book.title} is not in circulation", param="book")
    if member.status != "active":
        raise Conflict(f"{member.name} is suspended", param="member")
    if available(svc, book) > 0:
        raise Conflict(f"a copy of {book.title} is available", param="book")
    if svc.store.open_loans(book_id=book.id, member_id=member.id) or any(
            r.member == member.id for r in svc.store.reservations_for(book.id, "waiting", "ready")):
        raise Conflict(f"{member.name} already has {book.title}", param="member")
    reservation = Reservation(id=svc.ids.new("reservation"), book=book.id, member=member.id, status="waiting",
                              pickup_by=None, created_at=now, updated_at=now)
    svc.store.reservations[reservation.id] = reservation
    view = reservation_view(reservation)
    svc.bus.emit("reservation.created", {"reservation": view})
    return view


@operation("reservation.cancel")
def cancel(svc, params):
    now = svc.clock.now()
    reservation = svc.store.get_reservation(validate.require_str(params, "reservation"))
    if reservation.status not in ("waiting", "ready"):
        raise Conflict(f"reservation {reservation.id} is {reservation.status}", param="reservation")
    was_ready = reservation.status == "ready"
    reservation.status = "cancelled"
    svc.store.bump(reservation, now)
    view = reservation_view(reservation)
    events = [("reservation.cancelled", {"reservation": view})]
    if was_ready:
        events.extend(offer(svc, svc.store.get_book(reservation.book), now))
    for type_, data in events:
        svc.bus.emit(type_, data)
    return view


@operation("reservation.retrieve")
def retrieve(svc, params):
    return reservation_view(svc.store.get_reservation(validate.require_str(params, "reservation")))
