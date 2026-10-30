"""The payroll report, as text or as CSV."""
from .money import format_cents, format_hours

TITLE = "Payroll report"
NAME_WIDTH = 12
REG_WIDTH = 7
OT_WIDTH = 6
GROSS_WIDTH = 12
GAP = "  "


def _short_name(name):
    """Names longer than NAME_WIDTH are cut to their first 9 characters plus '...'."""
    if len(name) <= NAME_WIDTH:
        return name
    return name[:NAME_WIDTH - 3] + "..."


def _line(name, regular, overtime, gross):
    return GAP.join([name.ljust(NAME_WIDTH), regular.rjust(REG_WIDTH),
                     overtime.rjust(OT_WIDTH), gross.rjust(GROSS_WIDTH)])


def render_text(rows):
    lines = [TITLE, "=" * len(TITLE)]
    if not rows:
        lines.append("No shifts.")
        return "\n".join(lines) + "\n"
    rule = GAP.join("-" * width for width in (NAME_WIDTH, REG_WIDTH, OT_WIDTH, GROSS_WIDTH))
    lines.append(_line("Employee", "Reg hrs", "OT hrs", "Gross"))
    lines.append(rule)
    for row in rows:
        lines.append(_line(_short_name(row.name), format_hours(row.regular_minutes),
                           format_hours(row.overtime_minutes), format_cents(row.gross_cents)))
    lines.append(rule)
    lines.append(_line("TOTAL",
                       format_hours(sum(row.regular_minutes for row in rows)),
                       format_hours(sum(row.overtime_minutes for row in rows)),
                       format_cents(sum(row.gross_cents for row in rows))))
    count = len(rows)
    lines.append(f"{count} employee" + ("" if count == 1 else "s"))
    return "\n".join(lines) + "\n"


WEEKLY_TITLE = "Weekly breakdown"
WEEK_WIDTH = 10


def render_weekly(week_rows):
    """One line per employee and pay week, from `weekly_breakdown`."""
    lines = [WEEKLY_TITLE, "=" * len(WEEKLY_TITLE)]
    if not week_rows:
        lines.append("No shifts.")
        return "\n".join(lines) + "\n"
    widths = (NAME_WIDTH, WEEK_WIDTH, REG_WIDTH, OT_WIDTH, GROSS_WIDTH)

    def line(name, week, regular, overtime, gross):
        return GAP.join([name.ljust(NAME_WIDTH), week.ljust(WEEK_WIDTH), regular.rjust(REG_WIDTH),
                         overtime.rjust(OT_WIDTH), gross.rjust(GROSS_WIDTH)])

    lines.append(line("Employee", "Week of", "Reg hrs", "OT hrs", "Gross"))
    lines.append(GAP.join("-" * width for width in widths))
    for row in week_rows:
        lines.append(line(_short_name(row.name), row.week_start.isoformat(),
                          format_hours(row.regular_minutes), format_hours(row.overtime_minutes),
                          format_cents(row.gross_cents)))
    return "\n".join(lines) + "\n"
