"""An append-only event log other systems can read."""


class EventLog:
    def __init__(self):
        self.entries = []

    def emit(self, kind, subject, **data):
        self.entries.append({"kind": kind, "subject": subject, **data})

    def of_kind(self, kind):
        return [e for e in self.entries if e["kind"] == kind]

    def for_subject(self, subject):
        return [e for e in self.entries if e["subject"] == subject]

    def clear(self):
        self.entries.clear()
