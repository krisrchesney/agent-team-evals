from . import validate
from .errors import Conflict
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


def list_(desk, ticket, limit=None, include_deleted=False):
    parent = desk.store.ticket(ticket, include_deleted)
    limit = validate.limit(limit, default=50)
    found = desk.store.comments_of(parent.id, include_deleted)
    return {"data": [comment_view(c) for c in found[:limit]], "has_more": len(found) > limit}


def delete(desk, comment_id):
    comment = desk.store.comment(comment_id)
    comment.deleted_at = desk.clock.now()
    desk.search.reindex(comment.ticket)
    desk.feed.record("comment.deleted", {"id": comment.id})
    return comment_view(comment)


def restore(desk, comment_id):
    store = desk.store
    comment = store.comment(comment_id, include_deleted=True)
    if comment.deleted_at is None:
        raise Conflict(f"comment {comment.id} is not deleted", param="comment")
    if store.ticket(comment.ticket, include_deleted=True).deleted_at is not None:
        raise Conflict(f"ticket {comment.ticket} is deleted", param="ticket")
    comment.deleted_at = None
    comment.deleted_with = None
    desk.search.reindex(comment.ticket)
    desk.feed.record("comment.restored", {"id": comment.id})
    return comment_view(comment)
