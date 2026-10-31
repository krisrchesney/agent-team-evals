from . import cache, limits, search, summaries, validate
from .errors import Conflict
from .models import Task
from .views import task_view


def create(svc, project, title, assignee=None, labels=(), due=None, priority=2):
    store = svc.store
    owner = store.project(project)
    if owner.archived:
        raise Conflict(f"project {owner.id} is archived", param="project")
    title = validate.text(title, "title")
    if assignee is not None:
        store.member(assignee, param="assignee")
    names = tuple(sorted({store.label(validate.label_name(n), param="labels").name for n in labels}))
    due = validate.due(due)
    priority = validate.priority(priority)
    limits.check_tasks(store, owner.id)
    now = svc.clock.now()
    task = Task(id=svc.ids.new("t"), project=owner.id, title=title, status="todo", assignee=assignee,
                labels=names, due=due, priority=priority, created_at=now, updated_at=now)
    store.add_task(task)
    search.index_task(svc, task.id)
    summaries.invalidate(owner.id)
    svc.outbox.emit("task.created", {"id": task.id, "project": owner.id})
    svc.audit.record("task.create", task.id, title)
    return task_view(store, task)


def get(svc, task_id):
    cached = cache.get(task_id)
    if cached is not None and task_id in svc.store.tasks:
        return cached
    view = task_view(svc.store, svc.store.task(task_id))
    cache.put(task_id, view)
    return view


def list_(svc, project=None, status=None, assignee=None, label=None, limit=None):
    store = svc.store
    limit = validate.limit(limit)
    if project is not None:
        found = store.tasks_of(store.project(project).id)
    else:
        found = list(store.tasks.values())
    if status is not None:
        found = [t for t in found if t.status == validate.status(status)]
    if assignee is not None:
        found = [t for t in found if t.assignee == store.member(assignee, param="assignee").id]
    if label is not None:
        name = store.label(validate.label_name(label)).name
        found = [t for t in found if name in t.labels]
    found.sort(key=lambda t: (t.created_at, int(t.id[1:])))
    return {"data": [task_view(store, t) for t in found[:limit]], "has_more": len(found) > limit}


def _changed(svc, task, type_, data=None):
    task.updated_at = svc.clock.now()
    cache.drop(task.id)
    summaries.invalidate(task.project)
    svc.outbox.emit(type_, {"id": task.id, **(data or {})})
    svc.audit.record(type_, task.id)


def update(svc, task_id, title=None, status=None, priority=None, due=None):
    task = svc.store.task(task_id)
    if title is not None:
        task.title = validate.text(title, "title")
    if priority is not None:
        task.priority = validate.priority(priority)
    if due is not None:
        task.due = validate.due(due)
    if status is not None:
        before, task.status = task.status, validate.status(status)
        if before != task.status:
            _changed(svc, task, "task.status_changed", {"from": before, "to": task.status})
            search.index_task(svc, task.id)
            return task_view(svc.store, task)
    _changed(svc, task, "task.updated")
    search.index_task(svc, task.id)
    return task_view(svc.store, task)


def assign(svc, task_id, assignee):
    task = svc.store.task(task_id)
    if assignee is not None:
        svc.store.member(assignee, param="assignee")
    task.assignee = assignee
    _changed(svc, task, "task.assigned", {"assignee": assignee})
    return task_view(svc.store, task)


def delete(svc, task_id):
    task = svc.store.task(task_id)
    svc.store.drop_task(task.id)
    cache.drop(task.id)
    search.drop(task.id)
    summaries.invalidate(task.project)
    svc.outbox.emit("task.deleted", {"id": task.id, "project": task.project})
    svc.audit.record("task.delete", task.id)
    return {"id": task.id, "deleted": True}
