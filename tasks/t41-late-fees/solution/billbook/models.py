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
    late_fees: int = 0     # cents of late fees assessed so far
    fees_paid: int = 0     # how much of `paid` went to late fees
    fee_periods: int = 0   # late periods already looked at by fee.assess


@dataclass
class Payment:
    id: str
    invoice: str
    amount: int
    at: object


@dataclass
class Fee:
    id: str
    invoice: str
    amount: int
    period: int
    created_at: object
    updated_at: object
    version: int = 1
