"""Revenue recognition: an invoice line is earned evenly over the days of its own period."""
from .errors import ValidationError


def recognized_cents(app, invoice_id, index, as_of):
    invoice = app.invoices.get(invoice_id)
    try:
        line = invoice.lines[index]
    except IndexError:
        raise ValidationError("no such invoice line", field="index") from None
    total_days = (line.period_end - line.period_start).days
    elapsed = min(max((as_of - line.period_start).days, 0), total_days)
    return (2 * line.amount_cents * elapsed + total_days) // (2 * total_days)


def deferred_cents(app, invoice_id, index, as_of):
    invoice = app.invoices.get(invoice_id)
    return invoice.lines[index].amount_cents - recognized_cents(app, invoice_id, index, as_of)


def recognized_for_customer(app, customer_id, as_of):
    total = 0
    for invoice in app.invoices.for_customer(customer_id):
        for i in range(len(invoice.lines)):
            total += recognized_cents(app, invoice.id, i, as_of)
    return total
