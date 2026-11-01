from dataclasses import dataclass, field


@dataclass
class Contact:
    id: str
    name: str
    emails: list
    phones: list
    company: str
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Activity:
    """Something that happened with a contact: a call, an email or a meeting."""
    id: str
    contact: str
    kind: str      # call | email | meeting
    note: str
    at: object
