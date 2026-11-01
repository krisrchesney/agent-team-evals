from dataclasses import dataclass

from . import money
from .errors import DuplicateAccount, InvalidAccount, UnknownAccount

KINDS = ("asset", "liability", "equity", "income", "expense")


@dataclass(frozen=True)
class Account:
    code: str
    name: str
    kind: str
    currency: str = "USD"

    @property
    def sign(self):
        """+1 for accounts that grow with debits (assets, expenses), -1 for the others."""
        return 1 if self.kind in ("asset", "expense") else -1


class Chart:
    def __init__(self):
        self._accounts = {}

    def create(self, code, name, kind, currency="USD"):
        if not isinstance(code, str) or not code.strip():
            raise InvalidAccount("account code must be a non-empty string", param="code")
        if kind not in KINDS:
            raise InvalidAccount(f"kind must be one of {', '.join(KINDS)}", param="kind")
        money.exponent(currency)
        code = code.strip()
        if code in self._accounts:
            raise DuplicateAccount(f"account {code} already exists", param="code")
        account = Account(code=code, name=name, kind=kind, currency=currency)
        self._accounts[code] = account
        return account

    def get(self, code):
        account = self._accounts.get(code)
        if account is None:
            raise UnknownAccount(f"no account {code!r}", param="account")
        return account

    def all(self, kind=None):
        return sorted((a for a in self._accounts.values() if kind in (None, a.kind)), key=lambda a: a.code)
