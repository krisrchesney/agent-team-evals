from . import cache, comments, exporter, labels, members, projects, ratelimit, reports, search, snapshot, summaries, tasks
from .clock import SystemClock
from .tenants import Registry


class Lanes:
    """The whole service. Every method but the tenant admin ones takes the tenant first and counts as one
    call against that tenant's rate limit."""

    def __init__(self, clock=None):
        self.clock = clock or SystemClock()
        self.subscribers = []
        self.tenants = Registry(self.clock, self.subscribers)
        for process_wide in (cache, ratelimit, search, summaries):
            process_wide.reset()

    def _enter(self, tenant):
        ctx = self.tenants.get(tenant)
        ratelimit.hit(tenant, self.clock.now())
        return ctx

    def subscribe(self, fn):
        self.subscribers.append(fn)

    # tenants

    def create_tenant(self, tenant_id, name):
        created = self.tenants.create(tenant_id, name)
        return {"id": created.tenant, "name": created.name}

    def list_tenants(self):
        return {"data": [{"id": t.tenant, "name": t.name} for t in self.tenants.all()]}

    def delete_tenant(self, tenant_id):
        gone = self.tenants.get(tenant_id)
        self.tenants.drop(gone.tenant)
        for process_wide in (cache, ratelimit, search, summaries):
            process_wide.drop_tenant(gone.tenant)
        return {"id": gone.tenant, "deleted": True}

    # projects

    def create_project(self, tenant, name):
        return projects.create(self._enter(tenant), name)

    def get_project(self, tenant, project_id):
        return projects.get(self._enter(tenant), project_id)

    def list_projects(self, tenant):
        return projects.list_(self._enter(tenant))

    def rename_project(self, tenant, project_id, name):
        return projects.rename(self._enter(tenant), project_id, name)

    def archive_project(self, tenant, project_id):
        return projects.archive(self._enter(tenant), project_id)

    def delete_project(self, tenant, project_id):
        return projects.delete(self._enter(tenant), project_id)

    # members

    def add_member(self, tenant, name, email):
        return members.add(self._enter(tenant), name, email)

    def get_member(self, tenant, member_id):
        return members.get(self._enter(tenant), member_id)

    def list_members(self, tenant):
        return members.list_(self._enter(tenant))

    def remove_member(self, tenant, member_id):
        return members.remove(self._enter(tenant), member_id)

    # labels

    def add_label(self, tenant, name, color="#888888"):
        return labels.add(self._enter(tenant), name, color)

    def list_labels(self, tenant):
        return labels.list_(self._enter(tenant))

    def tag_task(self, tenant, task_id, name):
        return labels.tag(self._enter(tenant), task_id, name)

    def untag_task(self, tenant, task_id, name):
        return labels.untag(self._enter(tenant), task_id, name)

    # tasks and comments

    def create_task(self, tenant, project, title, assignee=None, labels=(), due=None, priority=2):
        return tasks.create(self._enter(tenant), project, title, assignee, labels, due, priority)

    def get_task(self, tenant, task_id):
        return tasks.get(self._enter(tenant), task_id)

    def list_tasks(self, tenant, project=None, status=None, assignee=None, label=None, limit=None):
        return tasks.list_(self._enter(tenant), project, status, assignee, label, limit)

    def update_task(self, tenant, task_id, title=None, status=None, priority=None, due=None):
        return tasks.update(self._enter(tenant), task_id, title, status, priority, due)

    def assign_task(self, tenant, task_id, assignee):
        return tasks.assign(self._enter(tenant), task_id, assignee)

    def delete_task(self, tenant, task_id):
        return tasks.delete(self._enter(tenant), task_id)

    def add_comment(self, tenant, task, author, text):
        return comments.add(self._enter(tenant), task, author, text)

    def list_comments(self, tenant, task):
        return comments.list_(self._enter(tenant), task)

    # search, reports, exports

    def search(self, tenant, text, limit=None):
        return search.query(self._enter(tenant), text, limit)

    def project_summary(self, tenant, project):
        return reports.project_summary(self._enter(tenant), project)

    def workload(self, tenant):
        return reports.workload(self._enter(tenant))

    def overdue(self, tenant):
        return reports.overdue(self._enter(tenant))

    def label_counts(self, tenant):
        return reports.label_counts(self._enter(tenant))

    def export_tasks_csv(self, tenant, project):
        return exporter.tasks_csv(self._enter(tenant), project)

    def export_json(self, tenant):
        return exporter.everything(self._enter(tenant))

    # events, audit, persistence

    def drain(self, tenant):
        return self._enter(tenant).outbox.drain()

    def audit_log(self, tenant, limit=20):
        return self._enter(tenant).audit.recent(limit)

    def dump(self):
        return snapshot.dump(self.tenants)

    @classmethod
    def load(cls, data, clock=None):
        svc = cls(clock)
        snapshot.load(data, svc.tenants)
        return svc
