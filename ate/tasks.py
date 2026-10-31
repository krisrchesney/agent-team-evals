"""Task folders: tasks/<id>/{task.json, prompt.md, repo/, hidden_tests/, solution/}."""
import json
from dataclasses import dataclass
from pathlib import Path

from . import REPO_ROOT

TASKS_DIR = REPO_ROOT / "tasks"
REQUIRED = ("task.json", "prompt.md", "repo", "hidden_tests", "solution")


@dataclass
class Task:
    id: str
    root: Path
    meta: dict

    @property
    def prompt(self):
        return (self.root / "prompt.md").read_text(encoding="utf-8").strip()

    @property
    def repo(self):
        return self.root / "repo"

    @property
    def hidden_tests(self):
        return self.root / "hidden_tests"

    @property
    def solution(self):
        return self.root / "solution"

    @property
    def ask_user(self):
        """True when the stand-in user tool is on for this task (task.json "ask_user": true)."""
        return bool(self.meta.get("ask_user"))

    @property
    def answers(self):
        """The hidden answer sheet, next to repo/ (never copied into a worktree)."""
        return self.root / "answers.json"

    @property
    def test_timeout_s(self):
        return int(self.meta.get("test_timeout_s", 120))


def load_task(task_id):
    root = TASKS_DIR / task_id
    missing = [name for name in REQUIRED if not (root / name).exists()]
    if missing:
        raise FileNotFoundError(f"task {task_id} is missing {missing}")
    meta = json.loads((root / "task.json").read_text(encoding="utf-8"))
    if meta.get("id") != task_id:
        raise ValueError(f"task.json id {meta.get('id')!r} does not match folder {task_id!r}")
    return Task(task_id, root, meta)


def list_tasks():
    return sorted(p.name for p in TASKS_DIR.iterdir() if (p / "task.json").exists())


def resolve(selection):
    """'all' or a comma list of ids/prefixes (e.g. 't01,t02')."""
    ids = list_tasks()
    if selection in (None, "", "all"):
        return ids
    chosen = []
    for want in selection.split(","):
        hits = [i for i in ids if i == want or i.startswith(want + "-")]
        if not hits:
            raise SystemExit(f"no task matches {want!r}; have {ids}")
        chosen.extend(h for h in hits if h not in chosen)
    return chosen
