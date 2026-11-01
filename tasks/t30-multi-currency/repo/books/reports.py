from datetime import timedelta

from . import dates, money


class Reports:
    def __init__(self, chart, journal):
        self.chart = chart
        self.journal = journal

    def trial_balance(self, as_of=None):
        rows = []
        total_debit = total_credit = 0
        for account in self.chart.all():
            balance = self.journal.balance(account.code, as_of)
            if balance == 0:
                continue
            debit, credit = (balance, 0) if balance > 0 else (0, -balance)
            rows.append({"account": account.code, "name": account.name, "debit": debit, "credit": credit})
            total_debit += debit
            total_credit += credit
        return {"as_of": as_of, "rows": rows, "total_debit": total_debit, "total_credit": total_credit,
                "balanced": total_debit == total_credit}

    def _section(self, kind, as_of):
        rows = []
        total = 0
        for account in self.chart.all(kind):
            balance = account.sign * self.journal.balance(account.code, as_of)
            if balance == 0:
                continue
            rows.append({"account": account.code, "name": account.name, "balance": balance})
            total += balance
        return {"rows": rows, "total": total}

    def _period_section(self, kind, start, end):
        rows = []
        total = 0
        for account in self.chart.all(kind):
            change = account.sign * sum(p.amount for _, p in self.journal.lines(account.code, start, end))
            if change == 0:
                continue
            rows.append({"account": account.code, "name": account.name, "balance": change})
            total += change
        return {"rows": rows, "total": total}

    def balance_sheet(self, as_of=None):
        assets = self._section("asset", as_of)
        liabilities = self._section("liability", as_of)
        equity = self._section("equity", as_of)
        earnings = self._section("income", as_of)["total"] - self._section("expense", as_of)["total"]
        if earnings:
            equity["rows"].append({"account": "current-earnings", "name": "Current earnings", "balance": earnings})
            equity["total"] += earnings
        return {"as_of": as_of, "assets": assets, "liabilities": liabilities, "equity": equity,
                "balanced": assets["total"] == liabilities["total"] + equity["total"]}

    def income_statement(self, start, end):
        income = self._period_section("income", start, end)
        expenses = self._period_section("expense", start, end)
        return {"start": start, "end": end, "income": income, "expenses": expenses,
                "net": income["total"] - expenses["total"]}

    def statement(self, code, start=None, end=None):
        account = self.chart.get(code)
        opening = 0
        if start:
            day_before = dates.parse(start, "start") - timedelta(days=1)
            opening = account.sign * self.journal.balance(code, day_before.isoformat())
        running = opening
        lines = []
        for entry, posting in self.journal.lines(code, start, end):
            running += account.sign * posting.amount
            lines.append({"date": entry.date.isoformat(), "memo": entry.memo, "amount": posting.amount,
                          "balance": running, "display": money.format_amount(running)})
        return {"account": account.code, "name": account.name, "opening": opening, "lines": lines,
                "closing": running}
