from . import cache, limits, search, summaries, validate
from .errors import Conflict
from .models import Project
from .views import project_view


def create(svc, name):
    name = validate.text(name, "name", max_len=60)
    if svc.store.project_id_for_name(name):
        raise Conflict(f"a project called {name} already exists", param="name")
    limits.check_projects(svc.store)
    project = Project(id=svc.ids.new("p"), name=name, archived=False, created_at=svc.clock.now())
    svc.store.add_project(project)
    svc.outbox.emit("project.created", {"id": project.id})
    svc.audit.record("project.create", project.id, name)
    return project_view(svc.store, project)


def get(svc, project_id):
    return project_view(svc.store, svc.store.project(project_id))


def list_(svc):
    found = sorted(svc.store.projects.values(), key=lambda p: (p.name.lower(), p.id))
    return {"data": [project_view(svc.store, p) for p in found]}


def rename(svc, project_id, name):
    project = svc.store.project(project_id)
    name = validate.text(name, "name", max_len=60)
    holder = svc.store.project_id_for_name(name)
    if holder and holder != project.id:
        raise Conflict(f"a project called {name} already exists", param="name")
    svc.store.rename_project(project, name)
    svc.outbox.emit("project.renamed", {"id": project.id})
    svc.audit.record("project.rename", project.id, name)
    return project_view(svc.store, project)


def archive(svc, project_id):
    project = svc.store.project(project_id)
    project.archived = True
    svc.outbox.emit("project.archived", {"id": project.id})
    svc.audit.record("project.archive", project.id)
    return project_view(svc.store, project)


def delete(svc, project_id):
    project = svc.store.project(project_id)
    gone = svc.store.drop_project(project.id)
    for task_id in gone:
        cache.drop(task_id)
        search.drop(task_id)
    summaries.invalidate(project.id)
    svc.outbox.emit("project.deleted", {"id": project.id, "tasks": len(gone)})
    svc.audit.record("project.delete", project.id, f"{len(gone)} tasks")
    return {"id": project.id, "deleted": True}
