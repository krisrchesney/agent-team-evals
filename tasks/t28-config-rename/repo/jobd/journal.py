"""An append-only journal of job events, so a restart can see what was in flight."""
import json


class Journal:
    def __init__(self, path=None):
        self.path = path
        self.entries = []

    def record(self, event, job):
        entry = {"event": event, "job": job.id, "handler": job.handler, "attempts": job.attempts}
        self.entries.append(entry)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")
        return entry

    @staticmethod
    def read(path):
        with open(path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def unfinished(self):
        """Job ids that started but neither finished nor died."""
        open_ids = {}
        for entry in self.entries:
            if entry["event"] == "started":
                open_ids[entry["job"]] = entry
            elif entry["event"] in ("finished", "dead"):
                open_ids.pop(entry["job"], None)
        return sorted(open_ids)
