"""Group priced lines into report rows."""
from decimal import Decimal

from .config import OTHER_LABEL, TOTAL_LABEL, ZERO
from .labels import first_spelling, label_key
from .models import Group
from .money import quantize

DIMENSIONS = ("region", "product", "month")


def _month_label(line):
    return f"{line.txn.date.year:04d}-{line.txn.date.month:02d}"


def group_lines(lines, by="region"):
    """One Group per region, product or month. Regions and products are compared
    case-insensitively and keep the first spelling seen; they sort by label, case-insensitively.
    Months are labelled YYYY-MM and sort chronologically. A refunded line subtracts its
    units and revenue and does not count as an order."""
    groups = {}
    for line in lines:
        if by == "month":
            label = _month_label(line)
            key = label
        else:
            label = getattr(line.txn, by)
            key = label_key(label)
        group = groups.get(key)
        if group is None:
            group = groups[key] = Group(label if by == "month" else first_spelling(None, label))
        if line.txn.status == "refunded":
            group.units -= line.txn.qty
        else:
            group.orders += 1
            group.units += line.txn.qty
        group.revenue += line.usd
    return sorted(groups.values(), key=lambda g: g.label.lower())


def by_region(lines):
    return group_lines(lines, "region")


def _sum(label, groups):
    out = Group(label)
    for g in groups:
        out.orders += g.orders
        out.units += g.units
        out.revenue += g.revenue
    out.revenue = out.revenue + ZERO
    return out


def total(groups):
    """A Group named TOTAL that sums all the others."""
    return _sum(TOTAL_LABEL, groups)


def apply_top(groups, n):
    """The `n` groups with the most revenue (ties: label ascending), best first; any remaining
    groups are merged into one trailing 'Other' group."""
    ranked = sorted(groups, key=lambda g: (-g.revenue, g.label))
    kept, rest = ranked[:n], ranked[n:]
    if rest:
        kept.append(_sum(OTHER_LABEL, rest))
    return kept


def avg_order(group):
    """Revenue per order in cents, or None when the group has no orders."""
    if group.orders == 0:
        return None
    return quantize(group.revenue / group.orders, 2)


def share(group, total_group):
    """The group's percent of total revenue to one decimal; 0.0 when the total is zero."""
    if total_group.revenue == 0:
        return Decimal("0.0")
    return quantize(group.revenue * 100 / total_group.revenue, 1)
