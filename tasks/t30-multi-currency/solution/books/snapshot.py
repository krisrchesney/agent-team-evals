"""Save and load a ledger as plain data (JSON-friendly): the chart, the journal and the exchange rates."""
from datetime import date

from .accounts import Chart
from .fx import Rates
from .journal import Entry, Journal, Posting

VERSION = 2


def dump(chart, journal, rates):
    return {
        "version": VERSION,
        "accounts": [{"code": a.code, "name": a.name, "kind": a.kind, "currency": a.currency}
                     for a in chart.all()],
        "entries": [
            {"id": e.id, "date": e.date.isoformat(), "memo": e.memo, "ref": e.ref, "voids": e.voids,
             "postings": [{"account": p.account, "amount": p.amount, "currency": p.currency}
                          for p in e.postings]}
            for e in journal.entries
        ],
        "rates": rates.rows(),
    }


def load(data):
    """Version 1 data has no currencies or rates: everything in it is USD."""
    chart = Chart()
    for a in data["accounts"]:
        chart.create(a["code"], a["name"], a["kind"], a.get("currency", "USD"))
    journal = Journal(chart)
    for e in data["entries"]:
        postings = tuple(Posting(p["account"], p["amount"], p.get("currency", "USD")) for p in e["postings"])
        journal.entries.append(Entry(id=e["id"], date=date.fromisoformat(e["date"]), memo=e["memo"],
                                     postings=postings, ref=e.get("ref"), voids=e.get("voids")))
    rates = Rates()
    for r in data.get("rates", []):
        rates.set(r["base"], r["quote"], r["rate"], r["on"])
    return chart, journal, rates
