"""Tax breakdowns for statements and exports."""
from collections import defaultdict

from .money import basis_points_of, round_cents


def inclusive_split(gross_cents, bps):
    """Split a tax-inclusive price into (net, tax)."""
    net = round_cents(gross_cents * 10000 / (10000 + bps))
    return net, gross_cents - net


def tax_summary(app, start, end):
    """Tax collected per region on invoices issued in [start, end)."""
    totals = defaultdict(int)
    for invoice in app.invoices.all():
        if not start <= invoice.issued_on < end:
            continue
        customer = app.customers.get(invoice.customer)
        totals[customer.region or "unknown"] += invoice.tax_cents
    return dict(sorted(totals.items()))


def effective_rate_bps(invoice):
    """The tax rate an invoice actually paid, in basis points (0 for an empty or free invoice)."""
    if invoice.subtotal_cents == 0:
        return 0
    return round_cents(invoice.tax_cents * 10000 / invoice.subtotal_cents)


def retax(app, invoice):
    """What the tax on `invoice` would be under today's rate for the customer's region."""
    customer = app.customers.get(invoice.customer)
    rates = app.tax_rates.find_by_region(customer.region) if customer.region else []
    return basis_points_of(invoice.subtotal_cents, rates[0].bps) if rates else 0
