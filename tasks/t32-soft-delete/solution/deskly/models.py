from dataclasses import dataclass


@dataclass
class Customer:
    id: str
    name: str
    email: str            # always lower case
    created_at: object
    deleted_at: object = None
    deleted_with: str = None   # "customer:c1" when the row went with that parent, else None


@dataclass
class Ticket:
    id: str
    customer: str
    subject: str
    body: str
    status: str
    priority: int
    tags: tuple
    created_at: object
    updated_at: object
    deleted_at: object = None
    deleted_with: str = None   # "customer:c1" when the row went with that parent, else None


@dataclass
class Comment:
    id: str
    ticket: str
    author: str
    text: str
    created_at: object
    deleted_at: object = None
    deleted_with: str = None   # "ticket:t1" or "customer:c1" when the row went with that parent, else None
