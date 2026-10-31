from . import dates, money
from .errors import BudgetError


class Budgets:
    """Monthly spending limits on expense accounts."""

    def __init__(self, chart, journal, rates):
        self.chart = chart
        self.journal = journal
        self.rates = rates
        self._limits = {}

    def set(self, account, month, limit, currency=None):
        acct = self.chart.get(account)
        if acct.kind != "expense":
            raise BudgetError("budgets are for expense accounts", param="account")
        dates.month_bounds(month)
        currency = currency or acct.currency
        cents = money.parse_amount(limit, currency)
        if cents <= 0:
            raise BudgetError("limit must be positive", param="limit")
        self._limits[(acct.code, month)] = (cents, currency)
        return self.status(acct.code, month)

    def status(self, account, month):
        found = self._limits.get((account, month))
        if found is None:
            raise BudgetError(f"no budget for {account} in {month}", param="month")
        limit, currency = found
        first, last = dates.month_bounds(month)
        spent = sum(self.rates.convert(p.amount, p.currency, currency, e.date)
                    for e, p in self.journal.lines(account, first, last))
        percent = spent * 100 // limit if spent > 0 else 0
        return {"account": account, "month": month, "currency": currency, "limit": limit, "spent": spent,
                "remaining": limit - spent, "percent": percent, "over": spent > limit}

    def alerts(self, month, threshold=80):
        """Budgets for `month` that have used at least `threshold` percent, worst first."""
        found = [self.status(account, m) for (account, m) in sorted(self._limits) if m == month]
        found = [s for s in found if s["percent"] >= threshold]
        return sorted(found, key=lambda s: (-s["percent"], s["account"]))
