from dataclasses import dataclass


@dataclass
class Invoice:
    id: str
    customer: str
    amount: int       # cents
    due: object       # a date
    created_at: object
    updated_at: object
    paid: int = 0     # cents received so far
    status: str = "open"   # open | paid
    version: int = 1


@dataclass
class Payment:
    id: str
    invoice: str
    amount: int
    at: object
