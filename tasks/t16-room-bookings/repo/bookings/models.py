"""Plain data."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Room:
    id: str
    name: str
    capacity: int
    rate_cents: int  # per hour
    tier: str = "standard"  # "standard" or "premium"


@dataclass(frozen=True)
class User:
    id: str
    name: str
    role: str  # "admin", "manager", "staff" or "guest"
    team: str


@dataclass
class Team:
    name: str
    budget_cents: int  # what is left to spend
    spent_cents: int = 0  # charges minus refunds


@dataclass
class Booking:
    id: int
    room_id: str
    user_id: str
    team: str
    start: datetime
    end: datetime
    attendees: int
    cost_cents: int
    status: str = "active"  # "active" or "cancelled"
    created: datetime = None


@dataclass(frozen=True)
class Message:
    user_id: str
    subject: str
    body: str
