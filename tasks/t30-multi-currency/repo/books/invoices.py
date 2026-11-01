from datetime import timedelta

from . import dates, money
from .errors import InvoiceError, UnknownInvoice

BUCKETS = ("current", "1-30", "31-60", "61+")


def _bucket(days_overdue):
    if days_overdue <= 0:
        return "current"
    if days_overdue <= 30:
        return "1-30"
    if days_overdue <= 60:
        return "31-60"
    return "61+"


class Invoices:
    def __init__(self, journal):
        self.journal = journal
        self._invoices = {}

    def issue(self, number, customer, date, lines, receivable, revenue, tax_bp=0, tax_account=None, due_days=30):
        if number in self._invoices:
            raise InvoiceError(f"invoice {number} already exists", param="number")
        when = dates.parse(date)
        if not lines:
            raise InvoiceError("an invoice needs at least one line", param="lines")
        rows = []
        subtotal = 0
        for line in lines:
            quantity = line.get("quantity")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
                raise InvoiceError("quantity must be a positive whole number", param="quantity")
            unit = money.parse_amount(line.get("unit_price"))
            rows.append({"description": line.get("description", ""), "quantity": quantity,
                         "unit_price": unit, "total": quantity * unit})
            subtotal += quantity * unit
        tax = money.percent(subtotal, tax_bp)
        if tax and not tax_account:
            raise InvoiceError("tax_account is required when tax_bp is set", param="tax_account")
        total = subtotal + tax
        postings = [{"account": receivable, "amount": money.to_decimal_string(total)},
                    {"account": revenue, "amount": money.to_decimal_string(-subtotal)}]
        if tax:
            postings.append({"account": tax_account, "amount": money.to_decimal_string(-tax)})
        self.journal.post(when, f"invoice {number}", postings, ref=f"invoice:{number}")
        self._invoices[number] = {"number": number, "customer": customer, "date": when,
                                  "due": when + timedelta(days=due_days), "lines": rows, "subtotal": subtotal,
                                  "tax": tax, "total": total, "paid": 0, "receivable": receivable}
        return self.get(number)

    def get(self, number):
        inv = self._invoices.get(number)
        if inv is None:
            raise UnknownInvoice(f"no invoice {number!r}", param="number")
        outstanding = inv["total"] - inv["paid"]
        status = "paid" if outstanding == 0 else ("partial" if inv["paid"] else "open")
        return {**inv, "date": inv["date"].isoformat(), "due": inv["due"].isoformat(),
                "outstanding": outstanding, "status": status}

    def pay(self, number, date, amount, bank):
        inv = self._invoices.get(number)
        if inv is None:
            raise UnknownInvoice(f"no invoice {number!r}", param="number")
        cents = money.parse_amount(amount)
        if cents <= 0 or cents > inv["total"] - inv["paid"]:
            raise InvoiceError("payment must be positive and at most the amount outstanding", param="amount")
        self.journal.post(date, f"payment {number}",
                          [{"account": bank, "amount": money.to_decimal_string(cents)},
                           {"account": inv["receivable"], "amount": money.to_decimal_string(-cents)}],
                          ref=f"payment:{number}")
        inv["paid"] += cents
        return self.get(number)

    def aging(self, as_of):
        """Outstanding totals by how late they are as of `as_of`."""
        today = dates.parse(as_of, "as_of")
        totals = dict.fromkeys(BUCKETS, 0)
        for inv in self._invoices.values():
            outstanding = inv["total"] - inv["paid"]
            if outstanding > 0 and inv["date"] <= today:
                totals[_bucket((today - inv["due"]).days)] += outstanding
        return {"as_of": as_of, **totals, "total": sum(totals.values())}
