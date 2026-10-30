"""Glue: text in, report text out."""
from . import aggregate, validate
from .config import SKIPPED_SHOWN
from .export import render_json
from .parse import parse_text
from .render import render_csv, render_table
from .transform import price_lines


def skipped_block(issues):
    """'Skipped N invalid rows' plus the first few reasons ('rows' even when N is 1)."""
    lines = [f"Skipped {len(issues)} invalid rows"]
    lines += [f"  Line {i.line}: {i.message}" for i in issues[:SKIPPED_SHOWN]]
    if len(issues) > SKIPPED_SHOWN:
        lines.append(f"  ... and {len(issues) - SKIPPED_SHOWN} more")
    return "\n".join(lines)


def build_report(text, as_json=False, by="region", top=None, title=None, fmt=None,
                 date_from=None, date_to=None):
    """Return (report_text, issues) for the CSV `text`.

    `fmt` is 'table' (default), 'csv' or 'json'; `as_json` is the old spelling of fmt='json'.
    The skipped-rows block is part of the text only for the table format.
    """
    fmt = fmt or ("json" if as_json else "table")
    txns, issues = parse_text(text.splitlines())
    good, rejected = validate.split_valid(txns)
    issues = sorted(issues + rejected, key=lambda i: i.line)
    if date_from is not None:
        good = [t for t in good if t.date >= date_from]
    if date_to is not None:
        good = [t for t in good if t.date <= date_to]
    groups = aggregate.group_lines(price_lines(good), by)
    total = aggregate.total(groups)
    if top is not None:
        groups = aggregate.apply_top(groups, top)
    if fmt == "json":
        return render_json(groups, total), issues
    if fmt == "csv":
        return render_csv(groups, total), issues
    out = render_table(groups, total, by, title)
    if issues:
        out += "\n\n" + skipped_block(issues)
    return out, issues
