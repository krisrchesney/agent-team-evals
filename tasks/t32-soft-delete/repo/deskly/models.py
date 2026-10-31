from dataclasses import dataclass


@dataclass
class Customer:
    id: str
    name: str
    email: str            # always lower case
    created_at: object


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


@dataclass
class Comment:
    id: str
    ticket: str
    author: str
    text: str
    created_at: object
