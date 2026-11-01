from .errors import NotFound


class Store:
    def __init__(self):
        self.customers = {}
        self.invoices = {}

    def get_customer(self, customer_id):
        customer = self.customers.get(customer_id)
        if customer is None:
            raise NotFound(f"no customer {customer_id!r}", param="customer")
        return customer

    def get_invoice(self, invoice_id):
        invoice = self.invoices.get(invoice_id)
        if invoice is None:
            raise NotFound(f"no invoice {invoice_id!r}", param="invoice")
        return invoice
