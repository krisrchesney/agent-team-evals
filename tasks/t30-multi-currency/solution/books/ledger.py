from . import money, snapshot
from .accounts import Chart
from .budgets import Budgets
from .fx import Rates
from .interest import Interest
from .invoices import Invoices
from .journal import Journal
from .reconcile import Reconciler
from .recurring import Recurring
from .reports import Reports


def entry_view(entry):
    return {"id": entry.id, "date": entry.date.isoformat(), "memo": entry.memo, "ref": entry.ref,
            "voids": entry.voids,
            "postings": [{"account": p.account, "amount": p.amount, "currency": p.currency}
                         for p in entry.postings]}


class Ledger:
    def __init__(self, chart=None, journal=None, rates=None):
        self.chart = chart or Chart()
        self.journal = journal or Journal(self.chart)
        self.rates = rates or Rates()
        self.reports = Reports(self.chart, self.journal, self.rates)
        self.budgets = Budgets(self.chart, self.journal, self.rates)
        self.invoices = Invoices(self.journal, self.rates)
        self.recurring = Recurring(self.journal)
        self.interest = Interest(self.chart, self.journal)
        self.reconciler = Reconciler(self.journal)

    def create_account(self, code, name, kind, currency="USD"):
        account = self.chart.create(code, name, kind, currency)
        return {"code": account.code, "name": account.name, "kind": account.kind, "currency": account.currency}

    def post(self, date, memo, lines, ref=None):
        return entry_view(self.journal.post(date, memo, lines, ref=ref))

    def void(self, entry_id, date):
        return entry_view(self.journal.void(entry_id, date))

    def summary(self, as_of=None, currency="USD"):
        money.exponent(currency)

        def total(kind):
            balances = ((a, self.journal.balance(a.code, as_of)) for a in self.chart.all(kind))
            return sum(self.rates.convert(bal, a.currency, currency, as_of) for a, bal in balances if bal)

        assets = total("asset")
        liabilities = -total("liability")
        return {"accounts": len(self.chart.all()), "entries": len(self.journal.entries), "currency": currency,
                "assets": assets, "liabilities": liabilities, "net_worth": assets - liabilities}

    def dump(self):
        return snapshot.dump(self.chart, self.journal, self.rates)

    @classmethod
    def load(cls, data):
        chart, journal, rates = snapshot.load(data)
        return cls(chart, journal, rates)
