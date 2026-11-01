from .. import validate
from ..errors import Conflict
from ..models import Activity
from ..views import activity_view
from .registry import operation


@operation("activity.log")
def log(svc, params):
    now = svc.clock.now()
    contact = svc.store.get_contact(validate.require_str(params, "contact"))
    if contact.status == "merged":
        raise Conflict(f"contact {contact.id} was merged into {contact.merged_into}", param="contact")
    kind = validate.kind(params)
    note = validate.optional_str(params, "note", "")
    activity = Activity(id=svc.ids.new("activity"), contact=contact.id, kind=kind, note=note, at=now)
    svc.store.activities[activity.id] = activity
    view = activity_view(activity)
    svc.bus.emit("activity.logged", {"activity": view})
    return view


@operation("activity.list")
def list_activities(svc, params):
    contact = svc.store.get_contact(validate.require_str(params, "contact"))
    limit = validate.limit(params)
    rows = svc.store.activities_for(contact.id)
    return {"data": [activity_view(a) for a in rows[:limit]], "has_more": len(rows) > limit}
