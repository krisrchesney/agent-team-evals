from dataclasses import dataclass


@dataclass
class Customer:
    id: str
    name: str
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Invoice:
    """The bill for one customer's billing period. Invoices are never changed afterwards."""
    id: str
    customer: str
    lines: list    # dicts: meter, quantity, amount (cents)
    total: int     # cents
    created_at: object
