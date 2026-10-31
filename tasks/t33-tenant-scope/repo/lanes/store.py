"""In-memory tables and the indexes that go with them."""
from .errors import NotFound


class Store:
    def __init__(self):
        self.projects = {}
        self.members = {}
        self.labels = {}           # name -> Label
        self.tasks = {}
        self.comments = {}
        self._project_names = {}   # lower-case name -> project id
        self._emails = {}          # email -> member id
        self._tasks_of = {}        # project id -> {task id: None}, oldest first
        self._comments_of = {}     # task id -> [comment ids], oldest first

    # lookups

    def project(self, project_id, param="project"):
        found = self.projects.get(project_id)
        if found is None:
            raise NotFound(f"no project {project_id!r}", param=param)
        return found

    def member(self, member_id, param="member"):
        found = self.members.get(member_id)
        if found is None:
            raise NotFound(f"no member {member_id!r}", param=param)
        return found

    def label(self, name, param="label"):
        found = self.labels.get(name)
        if found is None:
            raise NotFound(f"no label {name!r}", param=param)
        return found

    def task(self, task_id, param="task"):
        found = self.tasks.get(task_id)
        if found is None:
            raise NotFound(f"no task {task_id!r}", param=param)
        return found

    def project_id_for_name(self, name):
        return self._project_names.get(name.lower())

    def member_id_for_email(self, email):
        return self._emails.get(email)

    def tasks_of(self, project_id):
        return [self.tasks[i] for i in self._tasks_of.get(project_id, ())]

    def comments_of(self, task_id):
        return [self.comments[i] for i in self._comments_of.get(task_id, ())]

    # writes

    def add_project(self, project):
        self.projects[project.id] = project
        self._project_names[project.name.lower()] = project.id

    def rename_project(self, project, name):
        del self._project_names[project.name.lower()]
        project.name = name
        self._project_names[name.lower()] = project.id

    def drop_project(self, project_id):
        """Remove a project with its tasks and their comments; returns the ids of the tasks that went."""
        project = self.projects.pop(project_id)
        del self._project_names[project.name.lower()]
        gone = list(self._tasks_of.pop(project_id, ()))
        for task_id in gone:
            self.tasks.pop(task_id)
            for comment_id in self._comments_of.pop(task_id, ()):
                del self.comments[comment_id]
        return gone

    def add_member(self, member):
        self.members[member.id] = member
        self._emails[member.email] = member.id

    def drop_member(self, member_id):
        member = self.members.pop(member_id)
        del self._emails[member.email]

    def add_label(self, label):
        self.labels[label.name] = label

    def add_task(self, task):
        self.tasks[task.id] = task
        self._tasks_of.setdefault(task.project, {})[task.id] = None

    def drop_task(self, task_id):
        task = self.tasks.pop(task_id)
        self._tasks_of[task.project].pop(task_id, None)
        for comment_id in self._comments_of.pop(task_id, ()):
            del self.comments[comment_id]

    def add_comment(self, comment):
        self.comments[comment.id] = comment
        self._comments_of.setdefault(comment.task, []).append(comment.id)
