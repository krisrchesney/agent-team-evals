"""Bulk import of customers and tax rates from CSV text."""
import csv
import io

from .errors import BillkitError, ValidationError


def _rows(text, required):
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in required if c not in (reader.fieldnames or [])]
    if missing:
        raise ValidationError(f"missing column {missing[0]!r}", field=missing[0])
    return list(reader)


def import_customers(app, text):
    """Create one customer per row. Returns (created, errors) where errors is [(line, message)]."""
    created, errors = [], []
    for line, row in enumerate(_rows(text, ["name", "email"]), start=2):
        try:
            created.append(app.customers.create(name=row["name"], email=row["email"],
                                                region=row.get("region") or ""))
        except BillkitError as exc:
            errors.append((line, exc.message))
    return created, errors


def import_tax_rates(app, text):
    created, errors = [], []
    for line, row in enumerate(_rows(text, ["region", "label", "bps"]), start=2):
        try:
            created.append(app.tax_rates.create(region=row["region"], label=row["label"], bps=int(row["bps"])))
        except (BillkitError, ValueError) as exc:
            errors.append((line, getattr(exc, "message", str(exc))))
    return created, errors


def find_customers(app, query):
    """Case-insensitive match on name or email."""
    q = query.strip().lower()
    if not q:
        return []
    return [c for c in app.customers.all() if q in c.name.lower() or q in c.email]
