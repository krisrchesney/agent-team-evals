from . import validate
from .models import Comment
from .views import comment_view


def add(desk, ticket, author, text):
    store = desk.store
    parent = store.ticket(ticket)
    author = validate.text(author, "author", max_len=60)
    text = validate.text(text, "text", max_len=2000)
    now = desk.clock.now()
    comment = Comment(id=desk.ids.new("m"), ticket=parent.id, author=author, text=text, created_at=now)
    store.add_comment(comment)
    parent.updated_at = now
    desk.search.reindex(parent.id)
    desk.feed.record("comment.added", {"id": comment.id, "ticket": parent.id})
    return comment_view(comment)


def list_(desk, ticket, limit=None):
    parent = desk.store.ticket(ticket)
    limit = validate.limit(limit, default=50)
    found = desk.store.comments_of(parent.id)
    return {"data": [comment_view(c) for c in found[:limit]], "has_more": len(found) > limit}


def delete(desk, comment_id):
    comment = desk.store.comment(comment_id)
    desk.store.drop_comment(comment.id)
    desk.search.reindex(comment.ticket)
    desk.feed.record("comment.deleted", {"id": comment.id})
    return {"id": comment.id, "deleted": True}
