"""Save and load a service as plain data (JSON-friendly): every tenant. Undelivered outbox events are not saved."""
from datetime import date, datetime

from . import search
from .models import Comment, Label, Member, Project, Task
from .views import stamp

VERSION = 2
LEGACY_TENANT = "default"


def _when(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")


def dump_tenant(t):
    store = t.store
    return {
        "id": t.tenant,
        "name": t.name,
        "ids": dict(t.ids.counters),
        "projects": [{"id": p.id, "name": p.name, "archived": p.archived, "created_at": stamp(p.created_at)}
                     for p in store.projects.values()],
        "members": [{"id": m.id, "name": m.name, "email": m.email} for m in store.members.values()],
        "labels": [{"name": l.name, "color": l.color} for l in store.labels.values()],
        "tasks": [{"id": x.id, "project": x.project, "title": x.title, "status": x.status,
                   "assignee": x.assignee, "labels": list(x.labels),
                   "due": x.due.isoformat() if x.due else None, "priority": x.priority,
                   "created_at": stamp(x.created_at), "updated_at": stamp(x.updated_at)}
                  for x in store.tasks.values()],
        "comments": [{"id": c.id, "task": c.task, "author": c.author, "text": c.text,
                      "created_at": stamp(c.created_at)} for c in store.comments.values()],
        "audit": [dict(e) for e in t.audit.entries],
    }


def load_tenant(data, t):
    """Fill an empty tenant from dumped data and rebuild its search index."""
    t.ids.counters = dict(data["ids"])
    for p in data["projects"]:
        t.store.add_project(Project(id=p["id"], name=p["name"], archived=p["archived"],
                                    created_at=_when(p["created_at"])))
    for m in data["members"]:
        t.store.add_member(Member(id=m["id"], name=m["name"], email=m["email"]))
    for l in data["labels"]:
        t.store.add_label(Label(name=l["name"], color=l["color"]))
    for x in data["tasks"]:
        t.store.add_task(Task(id=x["id"], project=x["project"], title=x["title"], status=x["status"],
                              assignee=x["assignee"], labels=tuple(x["labels"]),
                              due=date.fromisoformat(x["due"]) if x["due"] else None,
                              priority=x["priority"], created_at=_when(x["created_at"]),
                              updated_at=_when(x["updated_at"])))
    for c in data["comments"]:
        t.store.add_comment(Comment(id=c["id"], task=c["task"], author=c["author"], text=c["text"],
                                    created_at=_when(c["created_at"])))
    t.audit.entries = [dict(e) for e in data["audit"]]
    for task_id in t.store.tasks:
        search.index_task(t, task_id)


def dump(registry):
    return {"version": VERSION, "tenants": [dump_tenant(t) for t in registry.all()]}


def load(data, registry):
    """Version 1 data has no tenants: it becomes the tenant `default`."""
    bodies = data["tenants"] if "tenants" in data else [{**data, "id": LEGACY_TENANT, "name": "Default"}]
    for body in bodies:
        load_tenant(body, registry.create(body["id"], body["name"]))
