from .. import validate
from ..models import Fee
from ..views import fee_view, invoice_view
from .registry import operation

GRACE_DAYS = 5
PERIOD_DAYS = 30
RATE_PERCENT = 2
MINIMUM_FEE = 250
CAP_PERCENT = 25


def _assess_invoice(svc, invoice, now):
    overdue = (now.date() - invoice.due).days
    if invoice.status != "open" or overdue <= GRACE_DAYS:
        return []
    periods = 1 + (overdue - GRACE_DAYS - 1) // PERIOD_DAYS
    made = []
    for period in range(invoice.fee_periods + 1, periods + 1):
        invoice.fee_periods = period
        unpaid = invoice.amount - (invoice.paid - invoice.fees_paid)      # fees never count
        room = invoice.amount * CAP_PERCENT // 100 - invoice.late_fees
        amount = min(max(MINIMUM_FEE, unpaid * RATE_PERCENT // 100), room)
        if unpaid <= 0 or amount <= 0:
            continue
        fee = Fee(id=svc.ids.new("fee"), invoice=invoice.id, amount=amount, period=period,
                  created_at=now, updated_at=now)
        svc.store.fees[fee.id] = fee
        invoice.late_fees += amount
        svc.store.bump(invoice, now)
        view = fee_view(fee)
        svc.bus.emit("fee.assessed", {"fee": view, "invoice": invoice_view(invoice)})
        made.append(view)
    return made


@operation("fee.assess")
def assess(svc, params):
    now = svc.clock.now()
    if params.get("invoice") is not None:
        invoices = [svc.store.get_invoice(validate.require_str(params, "invoice"))]
    else:
        invoices = sorted(svc.store.invoices.values(), key=lambda i: (i.created_at, i.id))
    out = []
    for invoice in invoices:
        out.extend(_assess_invoice(svc, invoice, now))
    return {"data": out}


@operation("fee.list")
def list_fees(svc, params):
    invoice = svc.store.get_invoice(validate.require_str(params, "invoice"))
    limit = validate.limit(params)
    rows = svc.store.fees_for(invoice.id)
    return {"data": [fee_view(f) for f in rows[:limit]], "has_more": len(rows) > limit}
