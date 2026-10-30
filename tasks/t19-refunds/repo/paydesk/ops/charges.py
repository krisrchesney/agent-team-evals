"""Charge operations. This module is the reference for how an operation is built."""
from ..errors import InvalidRequest
from ..models import Charge
from ..money import check_amount, check_currency
from ..validate import check_id
from . import operation


@operation("charge.create", scope="charges:write")
def create(svc, ctx, *, account=None, amount=None, currency="USD"):
    check_id(account, "account")
    check_amount(amount)
    check_currency(currency)
    params = {"account": account, "amount": amount, "currency": currency}

    def body():
        now = svc.now()
        charge = Charge(id=svc.new_id("ch"), account=account, amount=amount, currency=currency,
                        created=now)
        svc.store.add_charge(charge)
        svc.audit.record(actor=ctx.actor, action="charge.create", object_id=charge.id, at=now,
                         details={"amount": amount, "currency": currency})
        out = charge.serialize()
        svc.events.emit("charge.created", out, at=now)
        return out

    return svc.idempotency.run(ctx, "charge.create", params, body)


@operation("charge.capture", scope="charges:write")
def capture(svc, ctx, *, charge_id=None, amount=None):
    check_id(charge_id, "charge_id")
    if amount is not None:
        check_amount(amount)
    params = {"charge_id": charge_id, "amount": amount}

    def body():
        charge = svc.store.get_charge(charge_id)
        if charge.status != "authorized":
            raise InvalidRequest(f"charge {charge_id} is {charge.status}, not authorized",
                                 code="charge_not_authorized", param="charge_id")
        captured = charge.amount if amount is None else amount
        if captured > charge.amount:
            raise InvalidRequest(f"cannot capture {captured}, only {charge.amount} was authorized",
                                 code="amount_too_large", param="amount")
        now = svc.now()
        svc.ledger.post(charge.id, charge.currency,
                        [(f"customer:{charge.account}", -captured), ("merchant_revenue", captured)])
        charge.amount_captured = captured
        charge.status = "captured"
        svc.audit.record(actor=ctx.actor, action="charge.capture", object_id=charge.id, at=now,
                         details={"amount": captured})
        out = charge.serialize()
        svc.events.emit("charge.captured", out, at=now)
        return out

    return svc.idempotency.run(ctx, "charge.capture", params, body)


@operation("charge.void", scope="charges:write")
def void(svc, ctx, *, charge_id=None):
    check_id(charge_id, "charge_id")
    params = {"charge_id": charge_id}

    def body():
        charge = svc.store.get_charge(charge_id)
        if charge.status != "authorized":
            raise InvalidRequest(f"charge {charge_id} is {charge.status}, not authorized",
                                 code="charge_not_authorized", param="charge_id")
        now = svc.now()
        charge.status = "voided"
        svc.audit.record(actor=ctx.actor, action="charge.void", object_id=charge.id, at=now, details={})
        out = charge.serialize()
        svc.events.emit("charge.voided", out, at=now)
        return out

    return svc.idempotency.run(ctx, "charge.void", params, body)


@operation("charge.retrieve", scope="charges:read")
def retrieve(svc, ctx, *, charge_id=None):
    check_id(charge_id, "charge_id")
    return svc.store.get_charge(charge_id).serialize()
