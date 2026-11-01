"""Save and load a service as plain data (JSON-friendly). Undelivered outbox events are not saved."""
from datetime import date, datetime

from . import search
from .models import Comment, Label, Member, Project, Task
from .views import stamp


def _when(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")


def dump(svc):
    store = svc.store
    return {
        "version": 1,
        "ids": dict(svc.ids.counters),
        "projects": [{"id": p.id, "name": p.name, "archived": p.archived, "created_at": stamp(p.created_at)}
                     for p in store.projects.values()],
        "members": [{"id": m.id, "name": m.name, "email": m.email} for m in store.members.values()],
        "labels": [{"name": l.name, "color": l.color} for l in store.labels.values()],
        "tasks": [{"id": t.id, "project": t.project, "title": t.title, "status": t.status,
                   "assignee": t.assignee, "labels": list(t.labels),
                   "due": t.due.isoformat() if t.due else None, "priority": t.priority,
                   "created_at": stamp(t.created_at), "updated_at": stamp(t.updated_at)}
                  for t in store.tasks.values()],
        "comments": [{"id": c.id, "task": c.task, "author": c.author, "text": c.text,
                      "created_at": stamp(c.created_at)} for c in store.comments.values()],
        "audit": [dict(e) for e in svc.audit.entries],
    }


def load(data, svc):
    """Fill an empty service from dumped data and rebuild the search index."""
    svc.ids.counters = dict(data["ids"])
    for p in data["projects"]:
        svc.store.add_project(Project(id=p["id"], name=p["name"], archived=p["archived"],
                                      created_at=_when(p["created_at"])))
    for m in data["members"]:
        svc.store.add_member(Member(id=m["id"], name=m["name"], email=m["email"]))
    for l in data["labels"]:
        svc.store.add_label(Label(name=l["name"], color=l["color"]))
    for t in data["tasks"]:
        svc.store.add_task(Task(id=t["id"], project=t["project"], title=t["title"], status=t["status"],
                                assignee=t["assignee"], labels=tuple(t["labels"]),
                                due=date.fromisoformat(t["due"]) if t["due"] else None,
                                priority=t["priority"], created_at=_when(t["created_at"]),
                                updated_at=_when(t["updated_at"])))
    for c in data["comments"]:
        svc.store.add_comment(Comment(id=c["id"], task=c["task"], author=c["author"], text=c["text"],
                                      created_at=_when(c["created_at"])))
    svc.audit.entries = [dict(e) for e in data["audit"]]
    for task_id in svc.store.tasks:
        search.index_task(svc, task_id)
