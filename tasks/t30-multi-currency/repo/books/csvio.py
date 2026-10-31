"""CSV export and import of journal entries, one row per posting."""
import csv

from . import money
from .errors import InvalidAmount

HEADER = ["entry", "date", "memo", "account", "amount"]


def _fmt(cents):
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100}.{abs(cents) % 100:02d}"


def export_entries(journal, fileobj):
    writer = csv.writer(fileobj, lineterminator="\n")
    writer.writerow(HEADER)
    for entry in sorted(journal.entries, key=lambda e: (e.date, e.id)):
        for posting in entry.postings:
            writer.writerow([entry.id, entry.date.isoformat(), entry.memo, posting.account, _fmt(posting.amount)])


def import_entries(journal, fileobj):
    """Post each entry found in the file (rows with the same `entry` value); returns the new entry ids."""
    groups = {}
    for number, row in enumerate(csv.DictReader(fileobj), start=2):
        try:
            money.parse_amount(row["amount"])
        except InvalidAmount as exc:
            raise InvalidAmount(f"row {number}: {exc.message}", param="amount") from None
        groups.setdefault(row["entry"], []).append(row)
    created = []
    for rows in groups.values():
        lines = [{"account": r["account"], "amount": r["amount"]} for r in rows]
        entry = journal.post(rows[0]["date"], rows[0]["memo"], lines)
        created.append(entry.id)
    return created
