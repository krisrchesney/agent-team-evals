from datetime import timedelta

from .. import validate
from ..errors import Conflict
from ..models import Voucher
from ..views import voucher_view
from .registry import operation

VALID_FOR = timedelta(days=365)


def _live(svc, params, now):
    svc.store.expire_vouchers(now)
    return svc.store.get_voucher(validate.require_str(params, "voucher"))


@operation("voucher.issue")
def issue(svc, params):
    now = svc.clock.now()
    amount = validate.cents(params, "amount")
    voucher = Voucher(id=svc.ids.new("voucher"), amount=amount, balance=amount, status="active",
                      expires_at=now + VALID_FOR, created_at=now, updated_at=now)
    svc.store.vouchers[voucher.id] = voucher
    view = voucher_view(voucher)
    svc.bus.emit("voucher.issued", {"voucher": view})
    return view


@operation("voucher.redeem")
def redeem(svc, params):
    now = svc.clock.now()
    voucher = _live(svc, params, now)
    order = svc.store.get_order(validate.require_str(params, "order"))
    if voucher.status != "active":
        raise Conflict(f"voucher {voucher.id} is {voucher.status}", param="voucher")
    if order.status != "open":
        raise Conflict(f"order {order.id} is already {order.status}", param="order")
    if order.voucher:
        raise Conflict(f"order {order.id} already has a voucher", param="order")
    applied = min(voucher.balance, order.total - order.credited)
    voucher.balance -= applied
    if voucher.balance == 0:
        voucher.status = "used"
    svc.store.bump(voucher, now)
    order.credited += applied
    order.voucher = voucher.id
    if order.credited == order.total:
        order.status = "paid"
    svc.store.bump(order, now)
    view = voucher_view(voucher)
    svc.bus.emit("voucher.redeemed", {"voucher": view})
    return view


@operation("voucher.void")
def void(svc, params):
    now = svc.clock.now()
    voucher = _live(svc, params, now)
    if voucher.status != "active" or voucher.balance != voucher.amount:
        raise Conflict(f"voucher {voucher.id} can no longer be voided", param="voucher")
    voucher.status = "void"
    voucher.balance = 0
    svc.store.bump(voucher, now)
    view = voucher_view(voucher)
    svc.bus.emit("voucher.voided", {"voucher": view})
    return view


@operation("voucher.retrieve")
def retrieve(svc, params):
    return voucher_view(_live(svc, params, svc.clock.now()))
