"""Append-only audit log: who did what to which object, and when."""


class AuditLog:
    def __init__(self):
        self.entries = []

    def record(self, *, actor, action, object_id, at, details=None):
        self.entries.append({"actor": actor, "action": action, "object_id": object_id, "at": at,
                             "details": dict(details or {})})

    def for_object(self, object_id):
        return [e for e in self.entries if e["object_id"] == object_id]
