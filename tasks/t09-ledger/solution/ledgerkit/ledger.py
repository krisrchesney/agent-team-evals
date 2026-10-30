"""A tiny in-memory ledger with holds, idempotency keys and reversals."""


class InsufficientFunds(Exception):
    pass


class KeyConflict(ValueError):
    pass


def _check_amount(amount):
    if type(amount) is not int or amount <= 0:
        raise ValueError(f"amount must be a positive int, got {amount!r}")


class Ledger:
    def __init__(self):
        self._balance = {}
        self._overdraft = {}
        self._history = {}
        self._holds = {}  # hold id -> (account, amount)
        self._txns = {}  # txn id -> {"kind", "src", "dst", "amount", "reversed"}
        self._keys = {}  # idempotency key -> ((src, dst, amount), txn id)
        self._next_txn = 1
        self._next_hold = 1

    def _account(self, name):
        if name not in self._balance:
            raise KeyError(name)
        return name

    def open_account(self, name, overdraft=0):
        if name in self._balance:
            raise ValueError(f"account {name!r} exists")
        if type(overdraft) is not int or overdraft < 0:
            raise ValueError("overdraft must be a non-negative int")
        self._balance[name] = 0
        self._overdraft[name] = overdraft
        self._history[name] = []

    def balance(self, name):
        return self._balance[self._account(name)]

    def available(self, name):
        held = sum(a for who, a in self._holds.values() if who == name)
        return self.balance(name) + self._overdraft[name] - held

    def total(self):
        return sum(self._balance.values())

    def history(self, name):
        return list(self._history[self._account(name)])

    def _post(self, kind, legs, amount, src=None, dst=None):
        txn_id = self._next_txn
        self._next_txn += 1
        for name, delta in legs:
            self._balance[name] += delta
            self._history[name].append((txn_id, delta))
        self._txns[txn_id] = {"kind": kind, "src": src, "dst": dst, "amount": amount, "reversed": False}
        return txn_id

    def _post_transfer(self, src, dst, amount):
        return self._post("transfer", [(src, -amount), (dst, amount)], amount, src, dst)

    def deposit(self, name, amount):
        _check_amount(amount)
        return self._post("deposit", [(self._account(name), amount)], amount)

    def withdraw(self, name, amount):
        _check_amount(amount)
        if amount > self.available(self._account(name)):
            raise InsufficientFunds(name)
        return self._post("withdraw", [(name, -amount)], amount)

    def transfer(self, src, dst, amount, key=None):
        _check_amount(amount)
        if src == dst:
            raise ValueError("cannot transfer to the same account")
        self._account(src)
        self._account(dst)
        signature = (src, dst, amount)
        if key is not None and key in self._keys:
            seen, txn_id = self._keys[key]
            if seen != signature:
                raise KeyConflict(key)
            return txn_id
        if amount > self.available(src):
            raise InsufficientFunds(src)
        txn_id = self._post_transfer(src, dst, amount)
        if key is not None:
            self._keys[key] = (signature, txn_id)
        return txn_id

    def hold(self, name, amount):
        _check_amount(amount)
        if amount > self.available(self._account(name)):
            raise InsufficientFunds(name)
        hold_id = self._next_hold
        self._next_hold += 1
        self._holds[hold_id] = (name, amount)
        return hold_id

    def release(self, hold_id):
        if hold_id not in self._holds:
            raise KeyError(hold_id)
        del self._holds[hold_id]

    def capture(self, hold_id, dst=None):
        if hold_id not in self._holds:
            raise KeyError(hold_id)
        name, amount = self._holds[hold_id]
        if dst is not None:
            self._account(dst)
            if dst == name:
                raise ValueError("cannot capture to the holder")
        del self._holds[hold_id]
        if dst is None:
            return self._post("withdraw", [(name, -amount)], amount)
        return self._post_transfer(name, dst, amount)

    def reverse(self, txn_id):
        txn = self._txns.get(txn_id)
        if txn is None:
            raise KeyError(txn_id)
        if txn["kind"] != "transfer" or txn["reversed"]:
            raise ValueError(f"transaction {txn_id} cannot be reversed")
        if txn["amount"] > self.available(txn["dst"]):
            raise InsufficientFunds(txn["dst"])
        txn["reversed"] = True
        return self._post("reversal", [(txn["dst"], -txn["amount"]), (txn["src"], txn["amount"])],
                          txn["amount"], txn["dst"], txn["src"])
