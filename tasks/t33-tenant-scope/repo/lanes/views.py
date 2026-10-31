def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def project_view(store, project):
    return {"id": project.id, "name": project.name, "archived": project.archived,
            "created_at": stamp(project.created_at), "task_count": len(store.tasks_of(project.id))}


def member_view(member):
    return {"id": member.id, "name": member.name, "email": member.email}


def label_view(label):
    return {"name": label.name, "color": label.color}


def task_view(store, task):
    return {"id": task.id, "project": task.project, "title": task.title, "status": task.status,
            "assignee": task.assignee, "labels": list(task.labels),
            "due": task.due.isoformat() if task.due else None, "priority": task.priority,
            "created_at": stamp(task.created_at), "updated_at": stamp(task.updated_at),
            "comment_count": len(store.comments_of(task.id))}


def comment_view(comment):
    return {"id": comment.id, "task": comment.task, "author": comment.author, "text": comment.text,
            "created_at": stamp(comment.created_at)}
