"""Group priced lines into report rows."""
from .config import TOTAL_LABEL, ZERO
from .labels import first_spelling, label_key
from .models import Group


def by_region(lines):
    """One Group per region. Regions are compared case-insensitively and the label is the
    first spelling seen. Groups come back sorted by label, case-insensitively."""
    groups = {}
    for line in lines:
        key = label_key(line.txn.region)
        group = groups.get(key)
        if group is None:
            group = groups[key] = Group(first_spelling(None, line.txn.region))
        group.orders += 1
        group.units += line.txn.qty
        group.revenue += line.usd
    return sorted(groups.values(), key=lambda g: g.label.lower())


def total(groups):
    """A Group named TOTAL that sums all the others."""
    out = Group(TOTAL_LABEL)
    for g in groups:
        out.orders += g.orders
        out.units += g.units
        out.revenue += g.revenue
    out.revenue = out.revenue + ZERO
    return out
