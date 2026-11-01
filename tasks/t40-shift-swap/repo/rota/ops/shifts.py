from .. import validate
from ..errors import Conflict
from ..models import Shift
from ..views import shift_view
from .registry import operation


@operation("shift.create")
def create(svc, params):
    now = svc.clock.now()
    person = svc.store.get_staff(validate.require_str(params, "staff"))
    start, end = validate.shift_span(params)
    if svc.store.clashes(person.id, start, end):
        raise Conflict(f"{person.name} already has a shift then", param="start")
    shift = Shift(id=svc.ids.new("shift"), staff=person.id, start=start, end=end, created_at=now, updated_at=now)
    svc.store.shifts[shift.id] = shift
    view = shift_view(shift)
    svc.bus.emit("shift.created", {"shift": view})
    return view


@operation("shift.retrieve")
def retrieve(svc, params):
    return shift_view(svc.store.get_shift(validate.require_str(params, "shift")))


@operation("shift.list")
def list_shifts(svc, params):
    limit = validate.limit(params)
    if params.get("staff") is not None:
        person = svc.store.get_staff(validate.require_str(params, "staff"))
        rows = svc.store.shifts_of(person.id)
    else:
        rows = sorted(svc.store.shifts.values(), key=lambda s: (s.start, s.id))
    return {"data": [shift_view(s) for s in rows[:limit]], "has_more": len(rows) > limit}
