"""CSV exports."""
import csv
import io

from .views import stamp


def _csv(header, rows):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


def tickets_csv(desk):
    rows = [[t.id, t.customer, t.subject, t.status, t.priority, " ".join(t.tags), stamp(t.created_at)]
            for t in desk.store.tickets.values()]
    return _csv(["id", "customer", "subject", "status", "priority", "tags", "created_at"], rows)


def customers_csv(desk):
    rows = [[c.id, c.name, c.email, len(desk.store.tickets_of(c.id)), stamp(c.created_at)]
            for c in desk.store.customers.values()]
    return _csv(["id", "name", "email", "tickets", "created_at"], rows)
