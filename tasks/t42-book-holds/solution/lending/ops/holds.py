from datetime import timedelta

from .. import validate
from ..errors import Conflict
from ..models import Hold, Loan
from ..views import hold_view
from .loans import LOAN_DAYS
from .registry import operation

MAX_ACTIVE = 3


def _live(svc, params, now):
    svc.store.expire_holds(now)
    return svc.store.get_hold(validate.require_str(params, "hold"))


def _overdue(svc, member, now):
    return any(loan.due < now for loan in svc.store.open_loans_of(member.id))


@operation("hold.place")
def place(svc, params):
    now = svc.clock.now()
    svc.store.expire_holds(now)
    book = svc.store.get_book(validate.require_str(params, "book"))
    member = svc.store.get_member(validate.require_str(params, "member"))
    loan = svc.store.open_loan_of(book.id)
    if loan and loan.member == member.id:
        raise Conflict(f"{member.name} has {book.title} on loan", param="member")
    if any(h.book == book.id for h in svc.store.active_holds_of(member.id)):
        raise Conflict(f"{member.name} already has a hold on {book.title}", param="member")
    if _overdue(svc, member, now):
        raise Conflict(f"{member.name} has an overdue loan", param="member")
    if len(svc.store.active_holds_of(member.id)) >= MAX_ACTIVE:
        raise Conflict(f"{member.name} already has {MAX_ACTIVE} holds", param="member")
    if not loan and not svc.store.ready_hold_of(book.id):
        raise Conflict(f"{book.title} is on the shelf", param="book")
    hold = Hold(id=svc.ids.new("hold"), book=book.id, member=member.id, status="waiting", expires_at=None,
                created_at=now, updated_at=now)
    svc.store.holds[hold.id] = hold
    view = hold_view(hold)
    svc.bus.emit("hold.placed", {"hold": view})
    return view


@operation("hold.cancel")
def cancel(svc, params):
    now = svc.clock.now()
    hold = _live(svc, params, now)
    if hold.status not in ("waiting", "ready"):
        raise Conflict(f"hold {hold.id} is {hold.status}", param="hold")
    was_ready = hold.status == "ready"
    hold.status = "cancelled"
    svc.store.bump(hold, now)
    if was_ready:
        svc.store.offer_next(hold.book, now)
    view = hold_view(hold)
    svc.bus.emit("hold.cancelled", {"hold": view})
    return view


@operation("hold.collect")
def collect(svc, params):
    now = svc.clock.now()
    hold = _live(svc, params, now)
    if hold.status != "ready":
        raise Conflict(f"hold {hold.id} is {hold.status}", param="hold")
    loan = Loan(id=svc.ids.new("loan"), book=hold.book, member=hold.member, due=now + timedelta(days=LOAN_DAYS),
                status="open", created_at=now, updated_at=now)
    svc.store.loans[loan.id] = loan
    hold.status = "collected"
    svc.store.bump(hold, now)
    view = hold_view(hold)
    svc.bus.emit("hold.collected", {"hold": view})
    return view


@operation("hold.retrieve")
def retrieve(svc, params):
    return hold_view(_live(svc, params, svc.clock.now()))
