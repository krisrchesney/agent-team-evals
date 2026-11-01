"""spendflow: employees and their expense claims for a small company. Money is whole cents (an int); times are
UTC; an expense `date` is a calendar day like 2026-01-02.

    from spendflow import Service
    svc = Service()
    boss = svc.call("employee.create", name="Dana")
    eve = svc.call("employee.create", name="Eve", manager=boss["id"])
    svc.call("expense.create", employee=eve["id"], amount=1850, date="2026-01-02", description="Train ticket")
"""
from .service import Service

__all__ = ["Service"]
