from datetime import timedelta
from fractions import Fraction

from . import dates, money
from .errors import InvalidAccount


class Interest:
    """Simple interest on a positive daily balance, posted as one entry."""

    def __init__(self, chart, journal):
        self.chart = chart
        self.journal = journal

    def accrue(self, account, annual_bp, start, end, income_account, post_date=None):
        """Interest for each day in [start, end), on that day's closing balance, rounded once at the end."""
        if self.chart.get(account).kind != "asset":
            raise InvalidAccount("interest accrues on asset accounts", param="account")
        if self.chart.get(income_account).kind != "income":
            raise InvalidAccount("interest is booked to an income account", param="income_account")
        first, last = dates.parse(start, "start"), dates.parse(end, "end")
        exact = Fraction(0)
        day = first
        while day < last:
            balance = self.journal.balance(account, day.isoformat())
            if balance > 0:
                exact += Fraction(balance * annual_bp, 10000 * 365)
            day += timedelta(days=1)
        cents = int((exact * 2 + 1) // 2)  # half up
        if cents == 0:
            return {"entry": None, "interest": 0, "display": money.format_amount(0)}
        entry = self.journal.post(post_date or last, f"interest {start}..{end}",
                                  [{"account": account, "amount": money.to_decimal_string(cents)},
                                   {"account": income_account, "amount": money.to_decimal_string(-cents)}],
                                  ref=f"interest:{account}")
        return {"entry": entry.id, "interest": cents, "display": money.format_amount(cents)}
