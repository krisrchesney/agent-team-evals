from . import cache, summaries, validate
from .errors import Conflict
from .models import Member
from .views import member_view


def add(svc, name, email):
    name = validate.text(name, "name", max_len=60)
    email = validate.email(email)
    if svc.store.member_id_for_email(email):
        raise Conflict(f"email {email} is already used", param="email")
    member = Member(id=svc.ids.new("u"), name=name, email=email)
    svc.store.add_member(member)
    svc.outbox.emit("member.added", {"id": member.id})
    svc.audit.record("member.add", member.id, email)
    return member_view(member)


def get(svc, member_id):
    return member_view(svc.store.member(member_id))


def list_(svc):
    found = sorted(svc.store.members.values(), key=lambda m: (m.name.lower(), m.id))
    return {"data": [member_view(m) for m in found]}


def remove(svc, member_id):
    """Remove a member; their tasks stay and become unassigned."""
    member = svc.store.member(member_id)
    now = svc.clock.now()
    freed = [t for t in svc.store.tasks.values() if t.assignee == member.id]
    for task in freed:
        task.assignee = None
        task.updated_at = now
        cache.drop(svc.tenant, task.id)
        summaries.invalidate(svc.tenant, task.project)
    svc.store.drop_member(member.id)
    svc.outbox.emit("member.removed", {"id": member.id, "unassigned": len(freed)})
    svc.audit.record("member.remove", member.id, f"{len(freed)} tasks unassigned")
    return {"id": member.id, "removed": True}
