from . import snapshot
from .accounts import Chart
from .budgets import Budgets
from .interest import Interest
from .invoices import Invoices
from .journal import Journal
from .reconcile import Reconciler
from .recurring import Recurring
from .reports import Reports


def entry_view(entry):
    return {"id": entry.id, "date": entry.date.isoformat(), "memo": entry.memo, "ref": entry.ref,
            "voids": entry.voids,
            "postings": [{"account": p.account, "amount": p.amount} for p in entry.postings]}


class Ledger:
    def __init__(self, chart=None, journal=None):
        self.chart = chart or Chart()
        self.journal = journal or Journal(self.chart)
        self.reports = Reports(self.chart, self.journal)
        self.budgets = Budgets(self.chart, self.journal)
        self.invoices = Invoices(self.journal)
        self.recurring = Recurring(self.journal)
        self.interest = Interest(self.chart, self.journal)
        self.reconciler = Reconciler(self.journal)

    def create_account(self, code, name, kind):
        account = self.chart.create(code, name, kind)
        return {"code": account.code, "name": account.name, "kind": account.kind}

    def post(self, date, memo, lines, ref=None):
        return entry_view(self.journal.post(date, memo, lines, ref=ref))

    def void(self, entry_id, date):
        return entry_view(self.journal.void(entry_id, date))

    def summary(self, as_of=None):
        assets = sum(self.journal.balance(a.code, as_of) for a in self.chart.all("asset"))
        liabilities = -sum(self.journal.balance(a.code, as_of) for a in self.chart.all("liability"))
        return {"accounts": len(self.chart.all()), "entries": len(self.journal.entries),
                "assets": assets, "liabilities": liabilities, "net_worth": assets - liabilities}

    def dump(self):
        return snapshot.dump(self.chart, self.journal)

    @classmethod
    def load(cls, data):
        chart, journal = snapshot.load(data)
        return cls(chart, journal)
