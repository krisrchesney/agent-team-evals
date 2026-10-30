"""Corvid: semicolon-separated, German dates and number format (docs/vendors/corvid.md)."""
from .. import dates, money, normalize
from ..records import InvoiceLine
from .base import BaseImporter, RowProblem, optional, required, whole_number

DATE_FORMAT = "%d.%m.%Y"


def _date(text):
    try:
        return dates.parse(text, DATE_FORMAT)
    except ValueError:
        raise RowProblem("bad_date") from None


class CorvidImporter(BaseImporter):
    vendor = "corvid"
    delimiter = ";"

    def parse_row(self, row):
        if optional(row, "Status") == "STORNO":
            return None
        invoice_id = required(row, "Rechnung")
        line_no = required(row, "Pos")
        if not line_no.isdigit():
            raise RowProblem("missing_field")
        sku = normalize.sku(required(row, "Artikel"))
        description = normalize.text(optional(row, "Bezeichnung"))
        qty = whole_number(required(row, "Menge"))
        try:
            unit_cents = money.to_cents(required(row, "Einzelpreis"), ",", ".")
        except ValueError:
            raise RowProblem("bad_amount") from None
        currency = optional(row, "Waehrung") or self.settings["currency"]
        if currency not in money.CURRENCIES:
            raise RowProblem("unknown_currency")
        invoice_date = _date(required(row, "Datum"))
        due = optional(row, "Faellig")
        due_date = _date(due) if due else self.default_due(invoice_date)
        return InvoiceLine(self.vendor, invoice_id, int(line_no), sku, description, qty, unit_cents,
                           currency, invoice_date, due_date)
