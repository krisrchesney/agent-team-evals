"""Exports: tasks as CSV, everything as one JSON-friendly dict."""
import csv
import io

from .views import label_view, member_view, project_view, task_view


def tasks_csv(svc, project):
    owner = svc.store.project(project)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["id", "title", "status", "assignee", "labels", "due", "priority"])
    for t in svc.store.tasks_of(owner.id):
        writer.writerow([t.id, t.title, t.status, t.assignee or "", " ".join(t.labels),
                         t.due.isoformat() if t.due else "", t.priority])
    return out.getvalue()


def everything(svc):
    store = svc.store
    return {"projects": [project_view(store, p) for p in store.projects.values()],
            "members": [member_view(m) for m in store.members.values()],
            "labels": [label_view(l) for l in store.labels.values()],
            "tasks": [task_view(store, t) for t in store.tasks.values()]}
