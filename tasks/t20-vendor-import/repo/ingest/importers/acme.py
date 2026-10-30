"""Acme: comma-separated, ISO dates, US number format (docs/vendors/acme.md)."""
from .. import dates, money, normalize
from ..records import InvoiceLine
from .base import BaseImporter, RowProblem, optional, required, whole_number

DATE_FORMAT = "%Y-%m-%d"


def _date(text):
    try:
        return dates.parse(text, DATE_FORMAT)
    except ValueError:
        raise RowProblem("bad_date") from None


class AcmeImporter(BaseImporter):
    vendor = "acme"
    delimiter = ","

    def parse_row(self, row):
        invoice_id = required(row, "invoice")
        line_no = required(row, "line")
        if not line_no.isdigit():
            raise RowProblem("missing_field")
        sku = normalize.sku(required(row, "sku"))
        description = normalize.text(optional(row, "desc"))
        qty = whole_number(required(row, "qty"))
        try:
            unit_cents = money.to_cents(required(row, "unit_price"), ".", ",")
        except ValueError:
            raise RowProblem("bad_amount") from None
        currency = optional(row, "currency") or self.settings["currency"]
        if currency not in money.CURRENCIES:
            raise RowProblem("unknown_currency")
        invoice_date = _date(required(row, "date"))
        due = optional(row, "due")
        due_date = _date(due) if due else self.default_due(invoice_date)
        return InvoiceLine(self.vendor, invoice_id, int(line_no), sku, description, qty, unit_cents,
                           currency, invoice_date, due_date)
