from datetime import timedelta

from . import dates, money


class Reports:
    def __init__(self, chart, journal, rates):
        self.chart = chart
        self.journal = journal
        self.rates = rates

    def trial_balance(self, as_of=None):
        rows = []
        totals = {}
        for account in self.chart.all():
            balance = self.journal.balance(account.code, as_of)
            if balance == 0:
                continue
            debit, credit = (balance, 0) if balance > 0 else (0, -balance)
            rows.append({"account": account.code, "name": account.name, "currency": account.currency,
                         "debit": debit, "credit": credit})
            total = totals.setdefault(account.currency, {"debit": 0, "credit": 0})
            total["debit"] += debit
            total["credit"] += credit
        usd = totals.get("USD", {"debit": 0, "credit": 0})
        return {"as_of": as_of, "rows": rows, "totals": totals, "total_debit": usd["debit"],
                "total_credit": usd["credit"],
                "balanced": all(t["debit"] == t["credit"] for t in totals.values())}

    def _section(self, kind, as_of, currency):
        """Balances converted to `currency` one account at a time; also the native totals per currency."""
        rows = []
        total = 0
        native = {}
        for account in self.chart.all(kind):
            balance = account.sign * self.journal.balance(account.code, as_of)
            if balance == 0:
                continue
            native[account.currency] = native.get(account.currency, 0) + balance
            converted = self.rates.convert(balance, account.currency, currency, as_of)
            rows.append({"account": account.code, "name": account.name, "balance": converted})
            total += converted
        return {"rows": rows, "total": total}, native

    def _period_section(self, kind, start, end, currency):
        rows = []
        total = 0
        for account in self.chart.all(kind):
            change = account.sign * sum(p.amount for _, p in self.journal.lines(account.code, start, end))
            if change == 0:
                continue
            converted = self.rates.convert(change, account.currency, currency, end)
            rows.append({"account": account.code, "name": account.name, "balance": converted})
            total += converted
        return {"rows": rows, "total": total}

    def balance_sheet(self, as_of=None, currency="USD"):
        money.exponent(currency)
        assets, native_assets = self._section("asset", as_of, currency)
        liabilities, native_liabilities = self._section("liability", as_of, currency)
        equity, native_equity = self._section("equity", as_of, currency)
        income, native_income = self._section("income", as_of, currency)
        expenses, native_expenses = self._section("expense", as_of, currency)
        earnings = income["total"] - expenses["total"]
        if earnings:
            equity["rows"].append({"account": "current-earnings", "name": "Current earnings", "balance": earnings})
            equity["total"] += earnings
        codes = set(native_assets) | set(native_liabilities) | set(native_equity) | set(native_income) | set(native_expenses)
        balanced = all(native_assets.get(c, 0) == native_liabilities.get(c, 0) + native_equity.get(c, 0)
                       + native_income.get(c, 0) - native_expenses.get(c, 0) for c in codes)
        return {"as_of": as_of, "currency": currency, "assets": assets, "liabilities": liabilities,
                "equity": equity, "balanced": balanced}

    def income_statement(self, start, end, currency="USD"):
        money.exponent(currency)
        income = self._period_section("income", start, end, currency)
        expenses = self._period_section("expense", start, end, currency)
        return {"start": start, "end": end, "currency": currency, "income": income, "expenses": expenses,
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
                          "balance": running, "display": money.format_amount(running, account.currency)})
        return {"account": account.code, "name": account.name, "currency": account.currency,
                "opening": opening, "lines": lines, "closing": running}
