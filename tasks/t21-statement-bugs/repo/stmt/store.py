"""Every version of every transaction we have received (docs/FEED.md)."""


class TxnStore:
    def __init__(self, txns=()):
        self._txns = []
        for txn in txns:
            self.add(txn)

    def add(self, txn):
        if txn.posted_at.tzinfo is None:
            raise ValueError("posted_at must be timezone-aware")
        self._txns.append(txn)

    def all(self, account_id=None):
        """Every version received, in arrival order."""
        return [t for t in self._txns if account_id is None or t.account_id == account_id]

    def current(self, account_id=None):
        """The latest version of each transaction (highest version; on a tie, the last received)."""
        latest = {}
        for txn in self.all(account_id):
            seen = latest.get(txn.external_id)
            if seen is None or txn.version >= seen.version:
                latest[txn.external_id] = txn
        return list(latest.values())
