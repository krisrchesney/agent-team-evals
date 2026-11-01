from dataclasses import dataclass, field


@dataclass
class Employee:
    """`manager` is the id of another employee, or None for somebody at the top."""
    id: str
    name: str
    manager: object
    created_at: object
    updated_at: object
    version: int = 1


@dataclass
class Expense:
    """`amount` is in cents, `date` a datetime.date (the day the money was spent)."""
    id: str
    employee: str
    amount: int
    date: object
    description: str
    status: str    # draft | submitted | approved | rejected
    created_at: object
    updated_at: object
    version: int = 1
    approvals: list = field(default_factory=list)    # ids of the employees who approved, in order
    reason: object = None
