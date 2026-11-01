from .. import validate
from ..models import Member
from ..views import member_view
from .registry import operation


@operation("member.create")
def create(svc, params):
    now = svc.clock.now()
    name = validate.require_str(params, "name")
    member = Member(id=svc.ids.new("member"), name=name, created_at=now, updated_at=now)
    svc.store.members[member.id] = member
    view = member_view(member)
    svc.bus.emit("member.created", {"member": view})
    return view


@operation("member.retrieve")
def retrieve(svc, params):
    return member_view(svc.store.get_member(validate.require_str(params, "member")))
