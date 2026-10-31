"""CSV and text exports."""
import csv
import io

from .money import format_cents
from .serializers import invoice_dict


def invoices_csv(app, customer_id=None):
    invoices = app.invoices.for_customer(customer_id) if customer_id else app.invoices.all()
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["id", "customer", "kind", "issued_on", "subtotal_cents", "tax_cents", "total_cents", "paid"])
    for inv in sorted(invoices, key=lambda i: i.id):
        d = invoice_dict(inv)
        writer.writerow([d["id"], d["customer"], d["kind"], d["issued_on"], d["subtotal_cents"], d["tax_cents"],
                         d["total_cents"], "yes" if d["paid_on"] else "no"])
    return out.getvalue()


def statement_text(app, customer_id):
    customer = app.customers.get(customer_id)
    lines = [f"Statement for {customer.name}", ""]
    for inv in sorted(app.invoices.for_customer(customer_id), key=lambda i: i.id):
        lines.append(f"{inv.id}  {inv.issued_on.isoformat()}  {inv.kind:<11} {format_cents(inv.total_cents):>14}")
        for line in inv.lines:
            lines.append(f"    {line.description:<44} {format_cents(line.amount_cents):>14}")
    balance = sum(i.total_cents for i in app.invoices.unpaid() if i.customer == customer_id)
    lines += ["", f"Balance due: {format_cents(balance)}"]
    return "\n".join(lines) + "\n"
