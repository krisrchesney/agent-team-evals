from datetime import timedelta

from .. import validate
from ..errors import Conflict, InvalidRequest
from ..models import Swap
from ..views import shift_view, swap_view
from .registry import operation

NOTICE = timedelta(hours=24)
LAPSE = timedelta(hours=48)
REST = timedelta(hours=10)


def _live(svc, params, now):
    svc.store.expire_swaps(now)
    return svc.store.get_swap(validate.require_str(params, "swap"))


def _pending(swap):
    if swap.status != "pending":
        raise Conflict(f"swap {swap.id} is {swap.status}", param="swap")


def _rested(svc, shift, person):
    """Every other shift of `person` must be at least REST away from `shift` (an overlap is a gap below REST)."""
    for other in svc.store.shifts_of(person.id):
        if other.id == shift.id:
            continue
        if other.end <= shift.start:
            gap = shift.start - other.end
        elif other.start >= shift.end:
            gap = other.start - shift.end
        else:
            return False
        if gap < REST:
            return False
    return True


@operation("swap.request")
def request(svc, params):
    now = svc.clock.now()
    svc.store.expire_swaps(now)
    shift = svc.store.get_shift(validate.require_str(params, "shift"))
    target = svc.store.get_staff(validate.require_str(params, "to_staff"), param="to_staff")
    if target.id == shift.staff:
        raise InvalidRequest("that person already has the shift", param="to_staff")
    if shift.start - now < NOTICE:
        raise Conflict("swaps need at least 24 hours notice", param="shift")
    if svc.store.pending_for(shift.id):
        raise Conflict(f"shift {shift.id} already has a pending swap", param="shift")
    swap = Swap(id=svc.ids.new("swap"), shift=shift.id, from_staff=shift.staff, to_staff=target.id,
                status="pending", expires_at=min(now + LAPSE, shift.start), created_at=now, updated_at=now)
    svc.store.swaps[swap.id] = swap
    view = swap_view(swap)
    svc.bus.emit("swap.requested", {"swap": view})
    return view


@operation("swap.accept")
def accept(svc, params):
    now = svc.clock.now()
    swap = _live(svc, params, now)
    _pending(swap)
    shift = svc.store.get_shift(swap.shift)
    target = svc.store.get_staff(swap.to_staff)
    if not _rested(svc, shift, target):
        raise Conflict(f"{target.name} would not get 10 hours of rest", param="to_staff")
    shift.staff = target.id
    svc.store.bump(shift, now)
    swap.status = "accepted"
    svc.store.bump(swap, now)
    view = swap_view(swap)
    svc.bus.emit("swap.accepted", {"swap": view, "shift": shift_view(shift)})
    return view


def _close(svc, params, status):
    now = svc.clock.now()
    swap = _live(svc, params, now)
    _pending(swap)
    swap.status = status
    svc.store.bump(swap, now)
    view = swap_view(swap)
    svc.bus.emit(f"swap.{status}", {"swap": view})
    return view


@operation("swap.decline")
def decline(svc, params):
    return _close(svc, params, "declined")


@operation("swap.cancel")
def cancel(svc, params):
    return _close(svc, params, "cancelled")


@operation("swap.retrieve")
def retrieve(svc, params):
    return swap_view(_live(svc, params, svc.clock.now()))
