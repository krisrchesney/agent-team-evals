"""The data every other module shares: catalog items and orders."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    sku: str
    name: str
    price_cents: int
    category: str = "general"
    taxable: bool = True
    bundle: tuple = None

    def __post_init__(self):
        if self.bundle is None:
            return
        ok = isinstance(self.bundle, (tuple, list)) and len(self.bundle) == 2
        if ok:
            n, m = self.bundle
            ok = all(type(v) is int for v in (n, m)) and n > m >= 1
        if not ok:
            raise ValueError(f"bundle must be (n, m) ints with n > m >= 1, got {self.bundle!r}")


@dataclass(frozen=True)
class Line:
    sku: str
    qty: int


@dataclass(frozen=True)
class Order:
    lines: tuple
    customer: str = ""
    coupons: tuple = ()
