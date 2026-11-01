from .errors import NotFound
from .models import Payment


class Store:
    def __init__(self):
        self.invoices = {}
        self.payments = []

    def get_invoice(self, invoice_id):
        invoice = self.invoices.get(invoice_id)
        if invoice is None:
            raise NotFound(f"no invoice {invoice_id!r}", param="invoice")
        return invoice

    def bump(self, record, now):
        record.version += 1
        record.updated_at = now

    def add_payment(self, ids, invoice, amount, now):
        payment = Payment(id=ids.new("payment"), invoice=invoice.id, amount=amount, at=now)
        self.payments.append(payment)
        return payment

    def payments_for(self, invoice_id):
        return [p for p in self.payments if p.invoice == invoice_id]
