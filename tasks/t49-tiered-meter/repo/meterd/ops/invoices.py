from .. import validate
from ..models import Invoice
from ..views import invoice_view, line_view
from .registry import operation


@operation("usage.record")
def record(svc, params):
    customer = svc.store.get_customer(validate.require_str(params, "customer"))
    meter = svc.meter(validate.require_str(params, "meter"))
    quantity = validate.require_qty(params)
    meter.record(customer.id, quantity)
    view = {"customer": customer.id, "meter": meter.name, "quantity": quantity,
            "total": meter.get(customer.id)}
    svc.bus.emit("usage.recorded", {"usage": view})
    return view


@operation("period.close")
def close(svc, params):
    """Bill a customer for the period and start the next one."""
    now = svc.clock.now()
    customer = svc.store.get_customer(validate.require_str(params, "customer"))
    lines = []
    for meter in svc.meters:
        lines.extend(meter.settle(customer.id))
    for meter in svc.meters:
        meter.forget(customer.id)
    invoice = Invoice(id=svc.ids.new("invoice"), customer=customer.id, lines=lines,
                      total=sum(line["amount"] for line in lines), created_at=now)
    svc.store.invoices[invoice.id] = invoice
    view = invoice_view(invoice)
    svc.bus.emit("invoice.created", {"invoice": view})
    for line in view["lines"]:
        svc.bus.emit("line.added", {"line": line})
    return view


@operation("invoice.retrieve")
def retrieve(svc, params):
    return invoice_view(svc.store.get_invoice(validate.require_str(params, "invoice")))
