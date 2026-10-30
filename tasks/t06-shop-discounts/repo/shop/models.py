"""The data every other module shares: catalog items and orders."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    sku: str
    name: str
    price_cents: int
    category: str = "general"
    taxable: bool = True


@dataclass(frozen=True)
class Line:
    sku: str
    qty: int


@dataclass(frozen=True)
class Order:
    lines: tuple
    customer: str = ""
