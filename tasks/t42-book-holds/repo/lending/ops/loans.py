from datetime import timedelta

from .. import validate
from ..errors import Conflict
from ..models import Loan
from ..views import loan_view
from .registry import operation

LOAN_DAYS = 14


@operation("loan.borrow")
def borrow(svc, params):
    now = svc.clock.now()
    book = svc.store.get_book(validate.require_str(params, "book"))
    member = svc.store.get_member(validate.require_str(params, "member"))
    if svc.store.open_loan_of(book.id):
        raise Conflict(f"{book.title} is already out", param="book")
    loan = Loan(id=svc.ids.new("loan"), book=book.id, member=member.id, due=now + timedelta(days=LOAN_DAYS),
                status="open", created_at=now, updated_at=now)
    svc.store.loans[loan.id] = loan
    view = loan_view(loan)
    svc.bus.emit("loan.borrowed", {"loan": view})
    return view


@operation("loan.return")
def return_(svc, params):
    now = svc.clock.now()
    loan = svc.store.get_loan(validate.require_str(params, "loan"))
    if loan.status != "open":
        raise Conflict(f"loan {loan.id} is already {loan.status}", param="loan")
    loan.status = "returned"
    svc.store.bump(loan, now)
    view = loan_view(loan)
    svc.bus.emit("loan.returned", {"loan": view})
    return view


@operation("loan.retrieve")
def retrieve(svc, params):
    return loan_view(svc.store.get_loan(validate.require_str(params, "loan")))
