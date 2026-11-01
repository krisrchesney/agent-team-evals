from .. import validate
from ..errors import Conflict
from ..views import balance, invoice_view, payment_view
from .registry import operation


@operation("invoice.pay")
def pay(svc, params):
    now = svc.clock.now()
    invoice = svc.store.get_invoice(validate.require_str(params, "invoice"))
    amount = validate.require_amount(params)
    if invoice.status == "paid":
        raise Conflict(f"invoice {invoice.id} is already paid", param="invoice")
    if amount > balance(invoice):
        raise Conflict(f"only {balance(invoice)} cents are owed", param="amount")
    invoice.paid += amount
    if balance(invoice) == 0:
        invoice.status = "paid"
    svc.store.bump(invoice, now)
    payment = svc.store.add_payment(svc.ids, invoice, amount, now)
    view = invoice_view(invoice)
    svc.bus.emit("invoice.paid", {"invoice": view, "payment": payment_view(payment)})
    return view


@operation("payment.list")
def list_payments(svc, params):
    invoice = svc.store.get_invoice(validate.require_str(params, "invoice"))
    limit = validate.limit(params)
    rows = svc.store.payments_for(invoice.id)
    return {"data": [payment_view(p) for p in rows[:limit]], "has_more": len(rows) > limit}
