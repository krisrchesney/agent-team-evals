from . import summaries, validate


def project_summary(svc, project):
    """Task counts for one project (memoized until a task in it changes)."""
    owner = svc.store.project(project)
    memo = summaries.get(svc.tenant, owner.id)
    if memo is not None:
        return memo
    counts = dict.fromkeys(validate.STATUSES, 0)
    tasks = svc.store.tasks_of(owner.id)
    for task in tasks:
        counts[task.status] += 1
    summary = {"project": owner.id, "name": owner.name, "tasks": len(tasks), **counts}
    summaries.put(svc.tenant, owner.id, summary)
    return summary


def workload(svc):
    """Every member with the number of unfinished tasks assigned to them, busiest first."""
    open_tasks = {}
    for task in svc.store.tasks.values():
        if task.assignee and task.status != "done":
            open_tasks[task.assignee] = open_tasks.get(task.assignee, 0) + 1
    rows = [{"member": m.id, "name": m.name, "open": open_tasks.get(m.id, 0)} for m in svc.store.members.values()]
    rows.sort(key=lambda r: (-r["open"], r["name"].lower(), r["member"]))
    return rows


def overdue(svc):
    """Unfinished tasks whose due date is before today, oldest due date first."""
    today = svc.clock.now().date()
    late = [t for t in svc.store.tasks.values() if t.due and t.due < today and t.status != "done"]
    late.sort(key=lambda t: (t.due, int(t.id[1:])))
    return [{"task": t.id, "project": t.project, "title": t.title, "due": t.due.isoformat(),
             "assignee": t.assignee} for t in late]


def label_counts(svc):
    counts = {}
    for task in svc.store.tasks.values():
        for name in task.labels:
            counts[name] = counts.get(name, 0) + 1
    return [{"label": name, "count": n} for name, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
