import json
import os

from . import atomicio
from .errors import IoFailure, NotFound
from .model import Task


class Store:
    def __init__(self, path, tasks=None, next_id=1):
        self.path = path
        self.tasks = list(tasks or [])
        self.next_id = next_id

    @classmethod
    def load(cls, path):
        """A missing file is an empty store. A file that cannot be read is an I/O failure."""
        if not os.path.exists(path):
            return cls(path)
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            tasks = [Task.from_dict(d) for d in data["tasks"]]
            return cls(path, tasks, data["next_id"])
        except (OSError, ValueError, KeyError, TypeError) as err:
            raise IoFailure(f"cannot read store {path}: {err}") from None

    def document(self):
        return {"version": 1, "next_id": self.next_id, "tasks": [t.to_dict() for t in self.tasks]}

    def save(self):
        text = json.dumps(self.document(), indent=2, ensure_ascii=False) + "\n"
        try:
            atomicio.write_text(self.path, text)
        except OSError as err:
            raise IoFailure(f"cannot write store {self.path}: {err.strerror or err}") from None

    def add(self, **fields):
        task = Task(id=self.next_id, **fields)
        self.next_id += 1
        self.tasks.append(task)
        return task

    def get(self, task_id):
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise NotFound(f"no task #{task_id}")

    def projects(self):
        return sorted({t.project for t in self.tasks})
