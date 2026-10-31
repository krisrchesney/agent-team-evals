from . import cache, validate
from .errors import Conflict
from .models import Label
from .views import label_view, task_view


def add(svc, name, color="#888888"):
    name = validate.label_name(name)
    color = validate.color(color)
    if name in svc.store.labels:
        raise Conflict(f"label {name} already exists", param="name")
    label = Label(name=name, color=color)
    svc.store.add_label(label)
    svc.outbox.emit("label.added", {"name": name})
    svc.audit.record("label.add", name)
    return label_view(label)


def list_(svc):
    return {"data": [label_view(l) for l in sorted(svc.store.labels.values(), key=lambda l: l.name)]}


def tag(svc, task_id, name):
    task = svc.store.task(task_id)
    label = svc.store.label(validate.label_name(name))
    if label.name not in task.labels:
        task.labels = tuple(sorted(task.labels + (label.name,)))
        task.updated_at = svc.clock.now()
        cache.drop(task.id)
        svc.outbox.emit("task.tagged", {"id": task.id, "label": label.name})
        svc.audit.record("task.tag", task.id, label.name)
    return task_view(svc.store, task)


def untag(svc, task_id, name):
    task = svc.store.task(task_id)
    name = validate.label_name(name)
    if name in task.labels:
        task.labels = tuple(l for l in task.labels if l != name)
        task.updated_at = svc.clock.now()
        cache.drop(task.id)
        svc.outbox.emit("task.untagged", {"id": task.id, "label": name})
        svc.audit.record("task.untag", task.id, name)
    return task_view(svc.store, task)
