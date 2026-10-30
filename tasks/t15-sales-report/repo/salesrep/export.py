"""Machine-readable output."""
import json

from .money import quantize


def _row(group):
    return {
        "group": group.label,
        "orders": group.orders,
        "units": group.units,
        "revenue": f"{quantize(group.revenue):.2f}",
    }


def render_json(groups, total_group):
    """{"rows": [...], "total": {...}} with revenue as a string of exactly two decimals."""
    payload = {"rows": [_row(g) for g in groups], "total": _row(total_group)}
    return json.dumps(payload, indent=2)
