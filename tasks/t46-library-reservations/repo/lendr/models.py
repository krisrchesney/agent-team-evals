from dataclasses import dataclass


@dataclass
class Book:
    id: str
    title: str
    copies: int
    status: str    # active | retired
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Member:
    id: str
    name: str
    status: str    # active | suspended
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Loan:
    id: str
    book: str
    member: str
    status: str    # open | returned
    due: object
    returned_at: object
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Fine:
    """Charged when a loan comes back late. Fines are never changed afterwards."""
    id: str
    loan: str
    member: str
    amount: int    # cents
    created_at: object
