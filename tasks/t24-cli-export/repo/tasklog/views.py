def task_line(task):
    line = f"#{task.id} [{task.status}] p{task.priority} {task.project}: {task.title}"
    if task.due:
        line += f" (due {task.due})"
    return line


def task_detail(task):
    rows = [("id", f"#{task.id}"), ("title", task.title), ("project", task.project),
            ("status", task.status), ("priority", str(task.priority)),
            ("tags", ", ".join(task.tags) or "-"), ("due", task.due or "-"), ("created", task.created)]
    return "\n".join(f"{name:<9}{value}" for name, value in rows)
