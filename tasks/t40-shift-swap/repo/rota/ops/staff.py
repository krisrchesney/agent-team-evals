from .. import validate
from ..models import Staff
from ..views import staff_view
from .registry import operation


@operation("staff.create")
def create(svc, params):
    now = svc.clock.now()
    name = validate.require_str(params, "name")
    person = Staff(id=svc.ids.new("staff"), name=name, created_at=now, updated_at=now)
    svc.store.staff[person.id] = person
    view = staff_view(person)
    svc.bus.emit("staff.created", {"staff": view})
    return view


@operation("staff.retrieve")
def retrieve(svc, params):
    return staff_view(svc.store.get_staff(validate.require_str(params, "staff")))
