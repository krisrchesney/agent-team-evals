from dataclasses import dataclass


@dataclass
class Order:
    id: str
    customer: str
    total: int     # cents
    status: str    # placed | paid | packed | shipped | delivered | cancelled
    created_at: object
    updated_at: object
    version: int = 1
