"""Save and load a ledger as plain data (JSON-friendly). Only the chart and the journal are saved."""
from datetime import date

from .accounts import Chart
from .journal import Entry, Journal, Posting

VERSION = 1


def dump(chart, journal):
    return {
        "version": VERSION,
        "accounts": [{"code": a.code, "name": a.name, "kind": a.kind} for a in chart.all()],
        "entries": [
            {"id": e.id, "date": e.date.isoformat(), "memo": e.memo, "ref": e.ref, "voids": e.voids,
             "postings": [{"account": p.account, "amount": p.amount} for p in e.postings]}
            for e in journal.entries
        ],
    }


def load(data):
    chart = Chart()
    for a in data["accounts"]:
        chart.create(a["code"], a["name"], a["kind"])
    journal = Journal(chart)
    for e in data["entries"]:
        postings = tuple(Posting(p["account"], p["amount"]) for p in e["postings"])
        journal.entries.append(Entry(id=e["id"], date=date.fromisoformat(e["date"]), memo=e["memo"],
                                     postings=postings, ref=e.get("ref"), voids=e.get("voids")))
    return chart, journal
