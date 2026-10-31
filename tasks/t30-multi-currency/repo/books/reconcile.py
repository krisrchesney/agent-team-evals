from . import dates, money


class Reconciler:
    """Match bank statement rows against the ledger lines of one account."""

    def __init__(self, journal):
        self.journal = journal

    def match(self, account, statement, tolerance="0.00", days=3):
        """statement: [{"date": "2026-01-03", "amount": "-12.50"}, ...]. Each ledger line is used once.

        A row matches the closest ledger line (by amount, then date, then position) whose amount is
        within `tolerance` and whose date is within `days`.
        """
        slack = money.parse_amount(tolerance)
        ledger = self.journal.lines(account)
        used = set()
        matched, unmatched_statement = [], []
        statement_total = 0
        for index, row in enumerate(statement):
            amount = money.parse_amount(row.get("amount"))
            when = dates.parse(row.get("date"))
            statement_total += amount
            best = None
            for pos, (entry, posting) in enumerate(ledger):
                gap = abs(posting.amount - amount)
                lag = abs((entry.date - when).days)
                if pos in used or gap > slack or lag > days:
                    continue
                if best is None or (gap, lag, pos) < best[0]:
                    best = ((gap, lag, pos), pos)
            if best is None:
                unmatched_statement.append(index)
                continue
            used.add(best[1])
            entry, posting = ledger[best[1]]
            matched.append({"statement": index, "entry": entry.id, "difference": amount - posting.amount})
        unmatched_ledger = [entry.id for pos, (entry, _) in enumerate(ledger) if pos not in used]
        ledger_total = sum(posting.amount for _, posting in ledger)
        return {"matched": matched, "unmatched_statement": unmatched_statement,
                "unmatched_ledger": unmatched_ledger, "statement_total": statement_total,
                "ledger_total": ledger_total,
                "display": {"statement": money.format_amount(statement_total),
                            "ledger": money.format_amount(ledger_total)}}
