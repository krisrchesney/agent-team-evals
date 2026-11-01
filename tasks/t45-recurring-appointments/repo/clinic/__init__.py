"""clinic: patients and appointments for a one-doctor practice. Times are UTC, written like 2026-01-12T09:00:00Z.

    from clinic import Service
    svc = Service()
    pat = svc.call("patient.create", name="Rae")
    svc.call("appointment.book", patient=pat["id"], start="2026-01-12T09:00:00Z", minutes=30)
"""
from .service import Service

__all__ = ["Service"]
