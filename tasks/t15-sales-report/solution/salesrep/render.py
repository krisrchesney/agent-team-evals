"""Fixed-width text table and CSV."""
import csv
import io

from . import aggregate
from .config import ELLIPSIS, GAP, MAX_LABEL_WIDTH, TOTAL_LABEL
from .money import format_money, plain_money
from .text import align_row, column_widths, rule

HEADERS = ("Orders", "Units", "Revenue", "Avg Order", "Share")


def shorten(label):
    """Labels over MAX_LABEL_WIDTH characters become their first 17 characters plus '...'."""
    if len(label) <= MAX_LABEL_WIDTH:
        return label
    return label[: MAX_LABEL_WIDTH - len(ELLIPSIS)] + ELLIPSIS


def _cells(group, total_group):
    avg = aggregate.avg_order(group)
    return (
        shorten(group.label),
        str(group.orders),
        str(group.units),
        format_money(group.revenue),
        "-" if avg is None else format_money(avg),
        f"{aggregate.share(group, total_group):.1f}%",
    )


def render_table(groups, total_group, by="region", title=None):
    """Optional centered title, header, a dashed rule, one line per group, a dashed rule, then
    the TOTAL line. The first column is left-aligned, the others right-aligned. Each column is as
    wide as its longest cell (header included); columns are separated by two spaces."""
    headers = (by.capitalize(),) + HEADERS
    rows = [_cells(g, total_group) for g in groups]
    total_row = _cells(total_group, total_group)
    widths = column_widths(headers, rows + [total_row])

    def fmt(cells):
        return GAP.join(align_row(cells, widths))

    rule_line = GAP.join(rule(widths))
    lines = []
    if title is not None:
        lines.append(" " * max((len(rule_line) - len(title)) // 2, 0) + title)
    lines += [fmt(headers), rule_line]
    lines += [fmt(r) for r in rows]
    lines += [rule_line, fmt(total_row)]
    return "\n".join(lines)


def csv_fields(group, total_group):
    avg = aggregate.avg_order(group)
    return [
        group.label,
        group.orders,
        group.units,
        plain_money(group.revenue),
        "" if avg is None else plain_money(avg),
        f"{aggregate.share(group, total_group):.1f}",
    ]


def render_csv(groups, total_group):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["group", "orders", "units", "revenue", "avg_order", "share"])
    for g in groups:
        writer.writerow(csv_fields(g, total_group))
    writer.writerow(csv_fields(total_group, total_group))
    return buf.getvalue().rstrip("\n")
