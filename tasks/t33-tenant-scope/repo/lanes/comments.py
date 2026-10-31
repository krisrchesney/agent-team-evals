from . import cache, search, validate
from .models import Comment
from .views import comment_view


def add(svc, task, author, text):
    store = svc.store
    parent = store.task(task)
    member = store.member(author, param="author")
    text = validate.text(text, "text", max_len=2000)
    now = svc.clock.now()
    comment = Comment(id=svc.ids.new("c"), task=parent.id, author=member.id, text=text, created_at=now)
    store.add_comment(comment)
    parent.updated_at = now
    cache.drop(parent.id)
    search.index_task(svc, parent.id)
    svc.outbox.emit("comment.added", {"id": comment.id, "task": parent.id})
    svc.audit.record("comment.add", comment.id, parent.id)
    return comment_view(comment)


def list_(svc, task):
    parent = svc.store.task(task)
    return {"data": [comment_view(c) for c in svc.store.comments_of(parent.id)]}
