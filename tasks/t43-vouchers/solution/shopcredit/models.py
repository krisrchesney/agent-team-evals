from dataclasses import dataclass


@dataclass
class Customer:
    id: str
    name: str
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Order:
    """`total` is in cents. An order is open until it is paid."""
    id: str
    customer: str
    total: int
    status: str    # open | paid
    created_at: object
    updated_at: object
    version: int = 1
    credited: int = 0
    voucher: str = ""    # the voucher applied to this order, if any


@dataclass
class Voucher:
    id: str
    amount: int
    balance: int
    status: str    # active | used | void | expired
    expires_at: object
    created_at: object
    updated_at: object
    version: int = 1
