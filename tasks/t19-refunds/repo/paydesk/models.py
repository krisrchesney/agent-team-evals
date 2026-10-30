"""Stored objects. Each has serialize(), the dict the API returns (docs/API.md)."""
from dataclasses import dataclass, field


@dataclass
class Charge:
    id: str
    account: str
    amount: int
    currency: str
    created: str
    status: str = "authorized"
    amount_captured: int = 0
    amount_refunded: int = 0
    refunds: list = field(default_factory=list)

    @property
    def refundable(self):
        return self.amount_captured - self.amount_refunded

    def serialize(self):
        return {
            "id": self.id,
            "object": "charge",
            "account": self.account,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "amount_captured": self.amount_captured,
            "amount_refunded": self.amount_refunded,
            "refunds": list(self.refunds),
            "created": self.created,
        }
