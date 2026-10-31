from .errors import QuotaExceeded

MAX_PROJECTS = 5
MAX_TASKS_PER_PROJECT = 20


def check_projects(store):
    if len(store.projects) >= MAX_PROJECTS:
        raise QuotaExceeded(f"at most {MAX_PROJECTS} projects", param="projects")


def check_tasks(store, project_id):
    if len(store.tasks_of(project_id)) >= MAX_TASKS_PER_PROJECT:
        raise QuotaExceeded(f"at most {MAX_TASKS_PER_PROJECT} tasks in a project", param="project")
