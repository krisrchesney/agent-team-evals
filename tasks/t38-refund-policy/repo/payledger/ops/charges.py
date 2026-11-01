from .. import validate
from ..models import Charge
from ..views import charge_view, entry_view
from .registry import operation


@operation("charge.create")
def create(svc, params):
    now = svc.clock.now()
    customer = validate.require_str(params, "customer")
    amount = validate.require_amount(params)
    tax = validate.optional_cents(params, "tax", 0, amount)
    description = validate.optional_str(params, "description", "charge")
    charge = Charge(id=svc.ids.new("charge"), customer=customer, amount=amount, tax=tax,
                    description=description, created_at=now, updated_at=now)
    svc.store.charges[charge.id] = charge
    entry = svc.store.add_entry(svc.ids, charge, "charge", amount, description, now)
    view = charge_view(charge)
    svc.bus.emit("charge.created", {"charge": view, "entry": entry_view(entry)})
    return view


@operation("charge.retrieve")
def retrieve(svc, params):
    return charge_view(svc.store.get_charge(validate.require_str(params, "charge")))


@operation("charge.list")
def list_charges(svc, params):
    limit = validate.limit(params)
    customer = validate.optional_str(params, "customer", None)
    charges = sorted(svc.store.charges.values(), key=lambda c: (c.created_at, c.id))
    if customer is not None:
        charges = [c for c in charges if c.customer == customer]
    return {"data": [charge_view(c) for c in charges[:limit]], "has_more": len(charges) > limit}
