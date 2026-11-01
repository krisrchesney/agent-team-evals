from dataclasses import dataclass


@dataclass
class Charge:
    id: str
    customer: str
    amount: int        # total in cents, tax included
    tax: int           # the part of amount that is tax, in cents
    description: str
    created_at: object
    updated_at: object
    refunded: int = 0  # cents handed back so far
    status: str = "succeeded"
    version: int = 1


@dataclass
class Entry:
    """One signed money movement on a charge. A charge is +amount, anything handed back is negative."""
    id: str
    charge: str
    kind: str      # charge | refund
    amount: int    # signed cents
    ref: str       # the charge description, or the refund reason
    at: object


@dataclass
class Refund:
    id: str
    charge: str
    amount: int
    tax: int
    reason: str
    approved_by: object
    created_at: object
    updated_at: object
    version: int = 1
