from dataclasses import dataclass


@dataclass
class Item:
    id: str
    sku: str
    name: str
    on_hand: int
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Movement:
    """One change to an item's on_hand count. Nothing else is a movement."""
    id: str
    item: str
    kind: str      # receive | ship | adjust
    delta: int     # signed change to on_hand
    ref: str       # order id, delivery note or adjustment reason
    at: object
