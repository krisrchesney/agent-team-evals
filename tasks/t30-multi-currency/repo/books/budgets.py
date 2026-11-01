from . import dates, money
from .errors import BudgetError


class Budgets:
    """Monthly spending limits on expense accounts."""

    def __init__(self, chart, journal):
        self.chart = chart
        self.journal = journal
        self._limits = {}

    def set(self, account, month, limit):
        acct = self.chart.get(account)
        if acct.kind != "expense":
            raise BudgetError("budgets are for expense accounts", param="account")
        dates.month_bounds(month)
        cents = money.parse_amount(limit)
        if cents <= 0:
            raise BudgetError("limit must be positive", param="limit")
        self._limits[(acct.code, month)] = cents
        return self.status(acct.code, month)

    def status(self, account, month):
        limit = self._limits.get((account, month))
        if limit is None:
            raise BudgetError(f"no budget for {account} in {month}", param="month")
        first, last = dates.month_bounds(month)
        spent = sum(p.amount for _, p in self.journal.lines(account, first, last))
        percent = spent * 100 // limit if spent > 0 else 0
        return {"account": account, "month": month, "limit": limit, "spent": spent,
                "remaining": limit - spent, "percent": percent, "over": spent > limit}

    def alerts(self, month, threshold=80):
        """Budgets for `month` that have used at least `threshold` percent, worst first."""
        found = [self.status(account, m) for (account, m) in sorted(self._limits) if m == month]
        found = [s for s in found if s["percent"] >= threshold]
        return sorted(found, key=lambda s: (-s["percent"], s["account"]))
