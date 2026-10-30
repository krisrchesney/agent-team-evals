"""Bolt: tab-separated, US dates, prices already in cents (docs/vendors/bolt.md)."""
from .. import dates, normalize
from ..records import InvoiceLine
from .base import BaseImporter, RowProblem, optional, required, whole_number

DATE_FORMAT = "%m/%d/%Y"


def _date(text):
    try:
        return dates.parse(text, DATE_FORMAT)
    except ValueError:
        raise RowProblem("bad_date") from None


class BoltImporter(BaseImporter):
    vendor = "bolt"
    delimiter = "\t"

    def parse_row(self, row):
        if optional(row, "State").lower() == "cancelled":
            return None
        invoice_id = required(row, "InvoiceNo")
        line_no = required(row, "LineNo")
        if not line_no.isdigit():
            raise RowProblem("missing_field")
        sku = normalize.sku(required(row, "Part"))
        description = normalize.text(optional(row, "Text"))
        qty = whole_number(required(row, "Qty"))
        cents = required(row, "PriceCents")
        if not cents.isdigit():
            raise RowProblem("bad_amount")
        invoice_date = _date(required(row, "InvDate"))
        due = optional(row, "DueDate")
        due_date = _date(due) if due else self.default_due(invoice_date)
        return InvoiceLine(self.vendor, invoice_id, int(line_no), sku, description, qty, int(cents),
                           self.settings["currency"], invoice_date, due_date)
