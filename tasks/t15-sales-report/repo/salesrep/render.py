"""Fixed-width text table."""
from .config import GAP
from .money import format_money
from .text import align_row, column_widths, rule

HEADERS = ("Region", "Orders", "Units", "Revenue")


def _cells(group):
    return (group.label, str(group.orders), str(group.units), format_money(group.revenue))


def render_table(groups, total_group):
    """Header, a dashed rule, one line per group, a dashed rule, then the TOTAL line.

    The first column is left-aligned, the others right-aligned. Each column is as wide as its
    longest cell (header included); columns are separated by two spaces.
    """
    rows = [_cells(g) for g in groups]
    total_row = _cells(total_group)
    widths = column_widths(HEADERS, rows + [total_row])

    def fmt(cells):
        return GAP.join(align_row(cells, widths))

    rule_line = GAP.join(rule(widths))
    lines = [fmt(HEADERS), rule_line]
    lines += [fmt(r) for r in rows]
    lines += [rule_line, fmt(total_row)]
    return "\n".join(lines)
