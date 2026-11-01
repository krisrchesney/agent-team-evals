"""CSV exports. With include_deleted the rows of deleted records are listed too, with a deleted_at column."""
import csv
import io

from .views import stamp


def _csv(header, rows):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


def _deleted_at(row):
    return stamp(row.deleted_at) if row.deleted_at is not None else ""


def tickets_csv(desk, include_deleted=False):
    rows = []
    for t in desk.store.all_tickets(include_deleted):
        row = [t.id, t.customer, t.subject, t.status, t.priority, " ".join(t.tags), stamp(t.created_at)]
        rows.append(row + [_deleted_at(t)] if include_deleted else row)
    header = ["id", "customer", "subject", "status", "priority", "tags", "created_at"]
    return _csv(header + ["deleted_at"] if include_deleted else header, rows)


def customers_csv(desk, include_deleted=False):
    rows = []
    for c in desk.store.all_customers(include_deleted):
        row = [c.id, c.name, c.email, len(desk.store.tickets_of(c.id)), stamp(c.created_at)]
        rows.append(row + [_deleted_at(c)] if include_deleted else row)
    header = ["id", "name", "email", "tickets", "created_at"]
    return _csv(header + ["deleted_at"] if include_deleted else header, rows)
