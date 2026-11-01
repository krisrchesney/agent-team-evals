"""CSV export and import of journal entries, one row per posting."""
import csv

from . import money
from .errors import InvalidAmount

HEADER = ["entry", "date", "memo", "account", "amount", "currency"]


def export_entries(journal, fileobj):
    writer = csv.writer(fileobj, lineterminator="\n")
    writer.writerow(HEADER)
    for entry in sorted(journal.entries, key=lambda e: (e.date, e.id)):
        for posting in entry.postings:
            writer.writerow([entry.id, entry.date.isoformat(), entry.memo, posting.account,
                             money.to_decimal_string(posting.amount, posting.currency), posting.currency])


def import_entries(journal, fileobj):
    """Post each entry found in the file (rows with the same `entry` value); returns the new entry ids.

    A file without a currency column (an older export) is read in each account's own currency.
    """
    groups = {}
    for number, row in enumerate(csv.DictReader(fileobj), start=2):
        currency = journal.chart.get(row["account"]).currency
        try:
            money.parse_amount(row["amount"], currency)
        except InvalidAmount as exc:
            raise InvalidAmount(f"row {number}: {exc.message}", param="amount") from None
        groups.setdefault(row["entry"], []).append(row)
    created = []
    for rows in groups.values():
        lines = []
        for r in rows:
            line = {"account": r["account"], "amount": r["amount"]}
            if r.get("currency"):
                line["currency"] = r["currency"]
            lines.append(line)
        entry = journal.post(rows[0]["date"], rows[0]["memo"], lines)
        created.append(entry.id)
    return created
