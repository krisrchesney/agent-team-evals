from . import dates, money
from .errors import RecurringError, Unbalanced


class Recurring:
    """Entries that repeat every N months, posted when `run` is called."""

    def __init__(self, journal):
        self.journal = journal
        self._items = {}

    def add(self, name, start, lines, every_months=1, count=None, memo=None):
        if name in self._items:
            raise RecurringError(f"recurring entry {name} already exists", param="name")
        if every_months < 1:
            raise RecurringError("every_months must be at least 1", param="every_months")
        first = dates.parse(start, "start")
        total = 0
        for line in lines:
            self.journal.chart.get(line.get("account"))
            total += money.parse_amount(line.get("amount"))
        if total != 0:
            raise Unbalanced("a recurring entry must add up to zero", param="lines")
        self._items[name] = {"start": first, "every": every_months, "left": count, "lines": list(lines),
                             "memo": memo or name, "n": 0}

    def _next_date(self, item):
        return dates.add_months(item["start"], item["every"] * item["n"])

    def run(self, through):
        """Post every entry that is due on or before `through`; returns the new entry ids in order."""
        limit = dates.parse(through, "through")
        posted = []
        while True:
            due = [(self._next_date(item), name) for name, item in self._items.items()
                   if self._next_date(item) <= limit and (item["left"] is None or item["left"] > 0)]
            if not due:
                return posted
            when, name = min(due)
            item = self._items[name]
            entry = self.journal.post(when, item["memo"], item["lines"], ref=f"recurring:{name}")
            posted.append(entry.id)
            item["n"] += 1
            if item["left"] is not None:
                item["left"] -= 1
