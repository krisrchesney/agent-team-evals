"""Read the CSV text into transactions. Rows that cannot be read become Issues."""
import csv

from .dates import parse_iso
from .errors import ParseError
from .models import Issue, Txn
from .money import to_decimal

REQUIRED = ("id", "date", "region", "product", "qty", "unit_price")
DEFAULTS = {"discount_pct": "0", "currency": "USD", "status": "paid"}


def _parse_row(cells, line):
    """Return a Txn or an Issue for one non-blank row."""
    for name in REQUIRED:
        if not cells.get(name):
            return Issue(line, f"missing value for '{name}'")
    try:
        when = parse_iso(cells["date"])
    except ValueError:
        return Issue(line, f"bad date '{cells['date']}'")
    try:
        qty = int(cells["qty"])
    except ValueError:
        return Issue(line, f"bad quantity '{cells['qty']}'")
    try:
        price = to_decimal(cells["unit_price"])
    except ValueError:
        return Issue(line, f"bad price '{cells['unit_price']}'")
    discount_text = cells.get("discount_pct") or DEFAULTS["discount_pct"]
    try:
        discount = to_decimal(discount_text)
    except ValueError:
        return Issue(line, f"bad discount '{discount_text}'")
    return Txn(
        id=cells["id"],
        date=when,
        region=cells["region"],
        product=cells["product"],
        qty=qty,
        unit_price=price,
        discount_pct=discount,
        currency=(cells.get("currency") or DEFAULTS["currency"]).upper(),
        status=(cells.get("status") or DEFAULTS["status"]).lower(),
        line=line,
    )


def parse_text(lines):
    """Parse CSV lines (header first). Returns (txns, issues). Blank rows are ignored."""
    reader = csv.reader(lines)
    header = None
    txns, issues = [], []
    for row in reader:
        cells = [c.strip() for c in row]
        if not any(cells):
            continue
        if header is None:
            header = cells
            for name in REQUIRED:
                if name not in header:
                    raise ParseError(f"missing column '{name}'")
            continue
        cells += [""] * (len(header) - len(cells))
        parsed = _parse_row(dict(zip(header, cells)), reader.line_num)
        (issues if isinstance(parsed, Issue) else txns).append(parsed)
    if header is None:
        raise ParseError("empty input")
    return txns, issues
