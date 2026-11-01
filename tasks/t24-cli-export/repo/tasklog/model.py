from dataclasses import dataclass, field

STATUSES = ("open", "done")

FIELDS = ("id", "title", "project", "status", "priority", "tags", "due", "created")


@dataclass
class Task:
    id: int
    title: str
    project: str
    status: str
    priority: int
    created: str
    tags: list = field(default_factory=list)
    due: str = None

    def to_dict(self):
        """The task as scripts see it: `list --json`, `show --json` and backups all use this."""
        return {"id": self.id, "title": self.title, "project": self.project, "status": self.status,
                "priority": self.priority, "tags": list(self.tags), "due": self.due,
                "created": self.created}

    def to_row(self):
        """The task as one line of text cells, in FIELDS order."""
        return [str(self.id), self.title, self.project, self.status, str(self.priority),
                ";".join(self.tags), self.due or "", self.created]

    @classmethod
    def from_dict(cls, data):
        return cls(id=data["id"], title=data["title"], project=data["project"], status=data["status"],
                   priority=data["priority"], tags=list(data["tags"]), due=data["due"],
                   created=data["created"])
