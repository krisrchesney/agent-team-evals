from .. import validate
from ..models import Invoice
from ..views import invoice_view
from .registry import operation


@operation("invoice.create")
def create(svc, params):
    now = svc.clock.now()
    customer = validate.require_str(params, "customer")
    amount = validate.require_amount(params)
    due = validate.require_date(params, "due")
    invoice = Invoice(id=svc.ids.new("invoice"), customer=customer, amount=amount, due=due,
                      created_at=now, updated_at=now)
    svc.store.invoices[invoice.id] = invoice
    view = invoice_view(invoice)
    svc.bus.emit("invoice.created", {"invoice": view})
    return view


@operation("invoice.retrieve")
def retrieve(svc, params):
    return invoice_view(svc.store.get_invoice(validate.require_str(params, "invoice")))


@operation("invoice.list")
def list_invoices(svc, params):
    limit = validate.limit(params)
    customer = validate.optional_str(params, "customer", None)
    status = validate.optional_str(params, "status", None)
    rows = sorted(svc.store.invoices.values(), key=lambda i: (i.created_at, i.id))
    if customer is not None:
        rows = [i for i in rows if i.customer == customer]
    if status is not None:
        rows = [i for i in rows if i.status == status]
    return {"data": [invoice_view(i) for i in rows[:limit]], "has_more": len(rows) > limit}
