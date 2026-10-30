"""A tiny in-memory ledger."""


class InsufficientFunds(Exception):
    pass


class KeyConflict(ValueError):
    pass


class Ledger:
    def __init__(self):
        self._balances = {}

    def open_account(self, name):
        self._balances[name] = 0

    def balance(self, name):
        return self._balances[name]

    def deposit(self, name, amount):
        self._balances[name] += amount

    def withdraw(self, name, amount):
        if self._balances[name] < amount:
            raise InsufficientFunds(name)
        self._balances[name] -= amount

    def transfer(self, src, dst, amount):
        self.withdraw(src, amount)
        self.deposit(dst, amount)
