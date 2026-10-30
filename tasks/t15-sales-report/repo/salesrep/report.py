"""Glue: text in, report text out."""
from . import aggregate, validate
from .export import render_json
from .models import Issue
from .parse import parse_text
from .render import render_table
from .transform import price_lines


def build_report(text, as_json=False):
    """Return (report_text, issues) for the CSV `text`. With `as_json` the text is the JSON export."""
    txns, issues = parse_text(text.splitlines())
    good = []
    for txn in txns:
        problem = validate.check(txn)
        if problem:
            issues.append(Issue(txn.line, problem))
        else:
            good.append(txn)
    issues.sort(key=lambda i: i.line)
    groups = aggregate.by_region(price_lines(good))
    total = aggregate.total(groups)
    if as_json:
        return render_json(groups, total), issues
    out = render_table(groups, total)
    if issues:
        out += f"\n\nSkipped {len(issues)} invalid rows"
    return out, issues
