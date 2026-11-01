"""rota: staff and their shifts for a small restaurant. Times are UTC, written like 2026-01-12T09:00:00Z.

    from rota import Service
    svc = Service()
    cook = svc.call("staff.create", name="Mara")
    svc.call("shift.create", staff=cook["id"], start="2026-01-12T09:00:00Z", end="2026-01-12T17:00:00Z")
"""
from .service import Service

__all__ = ["Service"]
