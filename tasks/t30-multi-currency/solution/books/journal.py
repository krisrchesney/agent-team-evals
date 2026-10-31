from dataclasses import dataclass, field

from . import dates, money
from .errors import CurrencyMismatch, InvalidAmount, Unbalanced, UnknownEntry


@dataclass(frozen=True)
class Posting:
    account: str
    amount: int          # signed minor units of `currency`: debits are positive, credits negative
    currency: str = "USD"


@dataclass(frozen=True)
class Entry:
    id: str
    date: object
    memo: str
    postings: tuple
    ref: str = None
    voids: str = None


@dataclass
class Journal:
    chart: object
    entries: list = field(default_factory=list)

    def post(self, date, memo, lines, ref=None, voids=None):
        """lines: [{"account": "1000", "amount": "12.50"}, ...]; debits positive, credits negative.

        A line may also say {"currency": "EUR"}; it must be the account's currency.
        """
        when = dates.parse(date)
        if not isinstance(lines, (list, tuple)) or len(lines) < 2:
            raise Unbalanced("an entry needs at least two lines", param="lines")
        postings = []
        for line in lines:
            account = self.chart.get(line.get("account"))
            if line.get("currency", account.currency) != account.currency:
                raise CurrencyMismatch(f"account {account.code} is in {account.currency}, not {line['currency']}",
                                       param="currency")
            cents = money.parse_amount(line.get("amount"), account.currency)
            if cents == 0:
                raise InvalidAmount("a line cannot be zero", param="amount")
            postings.append(Posting(account.code, cents, account.currency))
        sums = {}
        for p in postings:
            sums[p.currency] = sums.get(p.currency, 0) + p.amount
        if any(sums.values()):
            raise Unbalanced("debits and credits must add up to zero in every currency", param="lines")
        return self._append(when, memo, postings, ref, voids)

    def _append(self, when, memo, postings, ref, voids):
        entry = Entry(id=f"e{len(self.entries) + 1}", date=when, memo=memo, postings=tuple(postings),
                      ref=ref, voids=voids)
        self.entries.append(entry)
        return entry

    def get(self, entry_id):
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        raise UnknownEntry(f"no entry {entry_id!r}", param="entry")

    def void(self, entry_id, date):
        """Post a reversing entry; the original stays in the journal."""
        original = self.get(entry_id)
        reversed_ = [Posting(p.account, -p.amount, p.currency) for p in original.postings]
        return self._append(dates.parse(date), f"void {original.id}", reversed_, f"void:{original.id}", original.id)

    def balance(self, code, as_of=None):
        """Signed balance in the account's minor units (debits positive) up to and including `as_of`."""
        self.chart.get(code)
        limit = dates.parse(as_of, "as_of") if as_of else None
        return sum(p.amount for e in self.entries if limit is None or e.date <= limit
                   for p in e.postings if p.account == code)

    def lines(self, code, start=None, end=None):
        """(entry, posting) pairs for one account, oldest first, within start..end inclusive."""
        self.chart.get(code)
        lo = dates.parse(start, "start") if start else None
        hi = dates.parse(end, "end") if end else None
        out = []
        for e in sorted(self.entries, key=lambda e: (e.date, e.id)):
            if (lo and e.date < lo) or (hi and e.date > hi):
                continue
            out.extend((e, p) for p in e.postings if p.account == code)
        return out
