from dataclasses import dataclass


@dataclass
class Member:
    id: str
    name: str
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Book:
    """One physical copy. It is on the shelf unless it has an open loan."""
    id: str
    title: str
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Loan:
    id: str
    book: str
    member: str
    due: object
    status: str    # open | returned
    created_at: object
    updated_at: object
    version: int = 1
