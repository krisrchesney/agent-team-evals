"""Price transactions in USD."""
from decimal import Decimal

from .fx import to_usd
from .models import Line
from .money import quantize


def net_amount(txn):
    """The discounted amount in the transaction's own currency.

    The discount comes off the unit price, and that discounted unit price is rounded to the
    smallest cent *before* it is multiplied by the quantity.
    """
    unit_net = quantize(txn.unit_price * (Decimal(100) - txn.discount_pct) / Decimal(100), 2)
    return unit_net * txn.qty


def price_lines(txns):
    """Void transactions are dropped silently; refunded ones are priced as negative revenue."""
    lines = []
    for txn in txns:
        if txn.status == "void":
            continue
        usd = to_usd(net_amount(txn), txn.currency)
        lines.append(Line(txn, -usd if txn.status == "refunded" else usd))
    return lines
