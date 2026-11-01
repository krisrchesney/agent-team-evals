from datetime import timedelta

from .. import validate
from ..errors import Conflict
from ..models import Refund
from ..views import charge_view, entry_view, refund_view
from .registry import operation

WINDOW = timedelta(days=30)
APPROVAL_OVER = 10_000


def _tax_portion(svc, charge, amount):
    remaining_tax = charge.tax - sum(r.tax for r in svc.store.refunds_for(charge.id))
    if charge.refunded + amount == charge.amount:
        return remaining_tax
    share = (2 * charge.tax * amount + charge.amount) // (2 * charge.amount)  # half up
    return min(remaining_tax, share)


@operation("refund.create")
def create(svc, params):
    now = svc.clock.now()
    charge = svc.store.get_charge(validate.require_str(params, "charge"))
    amount = validate.require_amount(params)
    reason = validate.optional_str(params, "reason", "customer request")
    if amount > APPROVAL_OVER:
        approved_by = validate.require_str(params, "approved_by")
    else:
        approved_by = validate.optional_str(params, "approved_by", None)
    if now - charge.created_at > WINDOW:
        raise Conflict(f"charge {charge.id} is too old to refund", param="charge")
    if amount > charge.amount - charge.refunded:
        raise Conflict(f"only {charge.amount - charge.refunded} cents left to refund", param="amount")
    tax = _tax_portion(svc, charge, amount)
    refund = Refund(id=svc.ids.new("refund"), charge=charge.id, amount=amount, tax=tax, reason=reason,
                    approved_by=approved_by, created_at=now, updated_at=now)
    svc.store.refunds[refund.id] = refund
    charge.refunded += amount
    charge.status = "refunded" if charge.refunded == charge.amount else "partially_refunded"
    svc.store.bump(charge, now)
    entry = svc.store.add_entry(svc.ids, charge, "refund", -amount, reason, now)
    view = refund_view(refund)
    svc.bus.emit("refund.created", {"refund": view, "entry": entry_view(entry)})
    return view


@operation("refund.retrieve")
def retrieve(svc, params):
    return refund_view(svc.store.get_refund(validate.require_str(params, "refund")))


@operation("refund.list")
def list_refunds(svc, params):
    charge = svc.store.get_charge(validate.require_str(params, "charge"))
    limit = validate.limit(params)
    rows = svc.store.refunds_for(charge.id)
    return {"data": [refund_view(r) for r in rows[:limit]], "has_more": len(rows) > limit}
