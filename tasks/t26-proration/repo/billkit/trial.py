"""Free trials."""
from datetime import timedelta

from .constants import TRIAL_DAYS
from .errors import Conflict


def trial_end(start, days=TRIAL_DAYS):
    return start + timedelta(days=days)


def start_trial(app, customer_id, plan_id, start, days=TRIAL_DAYS):
    """A trial is a subscription record with no invoice: it only reserves the plan."""
    app.customers.get(customer_id)
    app.catalog.get(plan_id)
    for note in app.notes.find_by_customer(customer_id):
        if note.body.startswith("trial:"):
            raise Conflict("customer already had a trial", field="customer")
    end = trial_end(start, days)
    app.notes.create(customer=customer_id, body=f"trial:{plan_id}:{start.isoformat()}:{end.isoformat()}",
                     author="system")
    app.events.emit("trial.started", customer_id, plan=plan_id, ends=end.isoformat())
    return end


def trial_for(app, customer_id):
    for note in app.notes.find_by_customer(customer_id):
        if note.body.startswith("trial:"):
            _, plan_id, start, end = note.body.split(":")
            return {"plan": plan_id, "start": start, "end": end}
    return None
