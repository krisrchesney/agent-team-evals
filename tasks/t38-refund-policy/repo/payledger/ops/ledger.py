from .. import validate
from ..views import entry_view
from .registry import operation


@operation("ledger.entries")
def entries(svc, params):
    charge = svc.store.get_charge(validate.require_str(params, "charge"))
    limit = validate.limit(params)
    rows = svc.store.entries_for(charge.id)
    return {"data": [entry_view(e) for e in rows[:limit]], "has_more": len(rows) > limit}
