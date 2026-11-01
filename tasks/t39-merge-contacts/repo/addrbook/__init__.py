"""addrbook: contacts and the calls, emails and meetings logged against them.

    from addrbook import Service
    svc = Service()
    c = svc.call("contact.create", name="Ada Lovelace", emails=["ada@example.com"])
    svc.call("activity.log", contact=c["id"], kind="call", note="Intro call")
"""
from .service import Service

__all__ = ["Service"]
