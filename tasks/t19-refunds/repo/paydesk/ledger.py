"""Double-entry ledger. Accounts and movements: docs/LEDGER.md."""


class UnbalancedTransaction(ValueError):
    pass


class Ledger:
    def __init__(self):
        self.transactions = []

    def post(self, ref, currency, entries):
        entries = [(account, amount) for account, amount in entries]
        if not entries or sum(amount for _, amount in entries) != 0:
            raise UnbalancedTransaction(f"entries for {ref} do not sum to zero: {entries}")
        self.transactions.append({"ref": ref, "currency": currency, "entries": entries})

    def balance(self, account, currency):
        return sum(amount for txn in self.transactions if txn["currency"] == currency
                   for acct, amount in txn["entries"] if acct == account)

    def for_ref(self, ref):
        return [txn for txn in self.transactions if txn["ref"] == ref]
