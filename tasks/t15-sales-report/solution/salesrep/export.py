"""Machine-readable output."""
import json

from . import aggregate
from .money import plain_money


def _row(group, total_group):
    avg = aggregate.avg_order(group)
    return {
        "group": group.label,
        "orders": group.orders,
        "units": group.units,
        "revenue": plain_money(group.revenue),
        "avg_order": None if avg is None else plain_money(avg),
        "share": f"{aggregate.share(group, total_group):.1f}",
    }


def render_json(groups, total_group):
    """{"rows": [...], "total": {...}}; amounts are strings with exactly two decimals."""
    payload = {"rows": [_row(g, total_group) for g in groups], "total": _row(total_group, total_group)}
    return json.dumps(payload, indent=2)
