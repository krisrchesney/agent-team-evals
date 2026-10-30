"""Accounts and transactions."""
import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    utc_offset_minutes: int = 0   # the account holder's time zone, e.g. 540 for Tokyo (UTC+9)


@dataclass(frozen=True)
class Txn:
    external_id: str
    account_id: str
    amount_cents: int             # money in is positive, money out negative
    posted_at: datetime.datetime  # aware, UTC
    description: str = ""
    version: int = 1
    status: str = "posted"        # "posted" or "pending"
