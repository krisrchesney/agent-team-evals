from . import cache, comments, exporter, labels, members, projects, ratelimit, reports, search, snapshot, summaries, tasks
from .audit import Audit
from .clock import SystemClock
from .ids import Ids
from .outbox import Outbox
from .store import Store


class Lanes:
    """The whole service. Every public method counts as one call against the rate limit."""

    def __init__(self, clock=None):
        self.clock = clock or SystemClock()
        self.store = Store()
        self.ids = Ids()
        self.outbox = Outbox(self.clock)
        self.audit = Audit(self.clock)
        for process_wide in (cache, ratelimit, search, summaries):
            process_wide.reset()

    def _enter(self):
        ratelimit.hit(self.clock.now())

    def subscribe(self, fn):
        self.outbox.subscribers.append(fn)

    # projects

    def create_project(self, name):
        self._enter()
        return projects.create(self, name)

    def get_project(self, project_id):
        self._enter()
        return projects.get(self, project_id)

    def list_projects(self):
        self._enter()
        return projects.list_(self)

    def rename_project(self, project_id, name):
        self._enter()
        return projects.rename(self, project_id, name)

    def archive_project(self, project_id):
        self._enter()
        return projects.archive(self, project_id)

    def delete_project(self, project_id):
        self._enter()
        return projects.delete(self, project_id)

    # members

    def add_member(self, name, email):
        self._enter()
        return members.add(self, name, email)

    def get_member(self, member_id):
        self._enter()
        return members.get(self, member_id)

    def list_members(self):
        self._enter()
        return members.list_(self)

    def remove_member(self, member_id):
        self._enter()
        return members.remove(self, member_id)

    # labels

    def add_label(self, name, color="#888888"):
        self._enter()
        return labels.add(self, name, color)

    def list_labels(self):
        self._enter()
        return labels.list_(self)

    def tag_task(self, task_id, name):
        self._enter()
        return labels.tag(self, task_id, name)

    def untag_task(self, task_id, name):
        self._enter()
        return labels.untag(self, task_id, name)

    # tasks and comments

    def create_task(self, project, title, assignee=None, labels=(), due=None, priority=2):
        self._enter()
        return tasks.create(self, project, title, assignee, labels, due, priority)

    def get_task(self, task_id):
        self._enter()
        return tasks.get(self, task_id)

    def list_tasks(self, project=None, status=None, assignee=None, label=None, limit=None):
        self._enter()
        return tasks.list_(self, project, status, assignee, label, limit)

    def update_task(self, task_id, title=None, status=None, priority=None, due=None):
        self._enter()
        return tasks.update(self, task_id, title, status, priority, due)

    def assign_task(self, task_id, assignee):
        self._enter()
        return tasks.assign(self, task_id, assignee)

    def delete_task(self, task_id):
        self._enter()
        return tasks.delete(self, task_id)

    def add_comment(self, task, author, text):
        self._enter()
        return comments.add(self, task, author, text)

    def list_comments(self, task):
        self._enter()
        return comments.list_(self, task)

    # search, reports, exports

    def search(self, text, limit=None):
        self._enter()
        return search.query(self, text, limit)

    def project_summary(self, project):
        self._enter()
        return reports.project_summary(self, project)

    def workload(self):
        self._enter()
        return reports.workload(self)

    def overdue(self):
        self._enter()
        return reports.overdue(self)

    def label_counts(self):
        self._enter()
        return reports.label_counts(self)

    def export_tasks_csv(self, project):
        self._enter()
        return exporter.tasks_csv(self, project)

    def export_json(self):
        self._enter()
        return exporter.everything(self)

    # events, audit, persistence

    def drain(self):
        self._enter()
        return self.outbox.drain()

    def audit_log(self, limit=20):
        self._enter()
        return self.audit.recent(limit)

    def dump(self):
        return snapshot.dump(self)

    @classmethod
    def load(cls, data, clock=None):
        svc = cls(clock)
        snapshot.load(data, svc)
        return svc
