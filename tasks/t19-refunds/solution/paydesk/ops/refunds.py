"""Refund operations (docs/API.md, Refunds)."""
from ..errors import InvalidRequest
from ..models import Refund
from ..money import check_amount
from ..validate import check_choice, check_id
from . import operation

REASONS = {"duplicate", "fraudulent", "requested_by_customer"}


@operation("refund.create", scope="refunds:write")
def create(svc, ctx, *, charge_id=None, amount=None, reason=None):
    check_id(charge_id, "charge_id")
    if amount is not None:
        check_amount(amount)
    if reason is not None:
        check_choice(reason, REASONS, "reason", "invalid_reason")
    params = {"charge_id": charge_id, "amount": amount, "reason": reason}

    def body():
        charge = svc.store.get_charge(charge_id)
        if charge.status == "refunded":
            raise InvalidRequest(f"charge {charge_id} is already fully refunded",
                                 code="charge_already_refunded", param="charge_id")
        if charge.status not in ("captured", "partially_refunded"):
            raise InvalidRequest(f"charge {charge_id} is {charge.status}, not captured",
                                 code="charge_not_captured", param="charge_id")
        refunded = charge.refundable if amount is None else amount
        if refunded > charge.refundable:
            raise InvalidRequest(f"cannot refund {refunded}, only {charge.refundable} is refundable",
                                 code="amount_too_large", param="amount")
        now = svc.now()
        refund = Refund(id=svc.new_id("re"), charge=charge.id, amount=refunded, currency=charge.currency,
                        reason=reason or "requested_by_customer", created=now)
        svc.ledger.post(refund.id, charge.currency,
                        [("merchant_revenue", -refunded), (f"customer:{charge.account}", refunded)])
        svc.store.add_refund(refund)
        charge.amount_refunded += refunded
        charge.refunds.append(refund.id)
        charge.status = "refunded" if charge.refundable == 0 else "partially_refunded"
        svc.audit.record(actor=ctx.actor, action="refund.create", object_id=refund.id, at=now,
                         details={"charge": charge.id, "amount": refunded})
        out = refund.serialize()
        svc.events.emit("refund.created", out, at=now)
        svc.events.emit("charge.refunded", charge.serialize(), at=now)
        return out

    return svc.idempotency.run(ctx, "refund.create", params, body)


@operation("refund.retrieve", scope="refunds:read")
def retrieve(svc, ctx, *, refund_id=None):
    check_id(refund_id, "refund_id")
    return svc.store.get_refund(refund_id).serialize()
