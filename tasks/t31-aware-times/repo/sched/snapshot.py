"""Save and load a scheduler as plain data (JSON-friendly)."""
from . import timeparse
from .events import rule_view

VERSION = 1


def dump(directory, calendars, events):
    return {
        "version": VERSION,
        "users": [{"id": u.id, "name": u.name, "hours": u.hours_view()} for u in directory.all()],
        "calendars": [{"id": c.id, "name": c.name} for c in calendars.all()],
        "events": [
            {"id": e.id, "calendar": e.calendar, "title": e.title, "start": timeparse.fmt_dt(e.start),
             "duration": int(e.duration.total_seconds() // 60), "attendees": list(e.attendees),
             "rule": rule_view(e.rule), "skips": sorted(d.isoformat() for d in e.skips),
             "status": e.status, "remind": list(e.remind)}
            for e in events.all(active_only=False)
        ],
    }


def load(data, sched):
    """Fill an empty Scheduler from dumped data."""
    for u in data["users"]:
        sched.directory.add(u["id"], u["name"], u["hours"])
    for c in data["calendars"]:
        sched.calendars.create(c["name"])
    for e in data["events"]:
        event = sched.events.create(e["calendar"], e["title"], e["start"], e["duration"], e["attendees"],
                                    e["rule"], e["remind"])
        event.id = e["id"]
        event.status = e["status"]
        event.skips = {timeparse.parse_date(d) for d in e["skips"]}
    sched.events._events = {e.id: e for e in sched.events._events.values()}
