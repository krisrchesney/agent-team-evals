"""CSV export of a statement's lines for customers who want a spreadsheet."""
import csv
import io


def to_csv(statement):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["external_id", "posted_at", "description", "amount_cents"])
    for txn in statement.lines:
        writer.writerow([txn.external_id, txn.posted_at.isoformat(), txn.description, txn.amount_cents])
    return buffer.getvalue()
