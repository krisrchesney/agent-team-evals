from datetime import timedelta

from .. import validate
from ..errors import Conflict, InsufficientStock
from ..models import Hold
from ..views import available, hold_view, movement_view
from .registry import operation

HOLD_FOR = timedelta(minutes=15)


@operation("hold.create")
def create(svc, params):
    now = svc.clock.now()
    svc.store.expire_holds(now)
    item = svc.store.get_item(validate.require_str(params, "item"))
    quantity = validate.require_qty(params)
    order = validate.require_str(params, "order")
    if quantity > available(svc, item):
        raise InsufficientStock(f"only {available(svc, item)} of {item.sku} available", param="quantity")
    hold = Hold(id=svc.ids.new("hold"), item=item.id, order=order, quantity=quantity, status="active",
                expires_at=now + HOLD_FOR, created_at=now, updated_at=now)
    svc.store.holds[hold.id] = hold
    view = hold_view(hold)
    svc.bus.emit("hold.created", {"hold": view})
    return view


def _active(svc, params, now):
    svc.store.expire_holds(now)
    hold = svc.store.get_hold(validate.require_str(params, "hold"))
    if hold.status != "active":
        raise Conflict(f"hold {hold.id} is {hold.status}", param="hold")
    return hold


@operation("hold.release")
def release(svc, params):
    now = svc.clock.now()
    hold = _active(svc, params, now)
    hold.status = "released"
    svc.store.bump(hold, now)
    view = hold_view(hold)
    svc.bus.emit("hold.released", {"hold": view})
    return view


@operation("hold.capture")
def capture(svc, params):
    now = svc.clock.now()
    hold = _active(svc, params, now)
    item = svc.store.get_item(hold.item)
    hold.status = "captured"
    svc.store.bump(hold, now)
    item.on_hand -= hold.quantity
    svc.store.bump(item, now)
    mv = svc.store.add_movement(svc.ids, item, "ship", -hold.quantity, hold.order, now)
    view = hold_view(hold)
    svc.bus.emit("hold.captured", {"hold": view, "movement": movement_view(mv)})
    return view


@operation("hold.retrieve")
def retrieve(svc, params):
    svc.store.expire_holds(svc.clock.now())
    return hold_view(svc.store.get_hold(validate.require_str(params, "hold")))
