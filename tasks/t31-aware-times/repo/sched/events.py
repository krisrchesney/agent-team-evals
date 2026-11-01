from dataclasses import dataclass, field

from . import timeparse
from .errors import InvalidRule, InvalidTime, UnknownEvent
from .users import WEEKDAYS

FREQUENCIES = ("daily", "weekly", "monthly")


@dataclass(frozen=True)
class Rule:
    freq: str
    interval: int = 1
    until: object = None       # last date a repeat may fall on, inclusive
    count: int = None          # number of repeats the rule generates, counting any that are skipped
    weekdays: tuple = ()       # weekly only: weekday numbers (Monday is 0); empty means the start's weekday


@dataclass
class Event:
    id: str
    calendar: str
    title: str
    start: object
    duration: object
    attendees: tuple = ()
    rule: Rule = None
    skips: set = field(default_factory=set)
    status: str = "active"
    remind: tuple = ()         # minutes before each occurrence


def parse_rule(data):
    if data is None:
        return None
    freq = data.get("freq")
    if freq not in FREQUENCIES:
        raise InvalidRule(f"freq must be one of {', '.join(FREQUENCIES)}", param="rule")
    interval = data.get("interval", 1)
    if isinstance(interval, bool) or not isinstance(interval, int) or interval < 1:
        raise InvalidRule("interval must be a positive whole number", param="rule")
    count = data.get("count")
    if count is not None and (isinstance(count, bool) or not isinstance(count, int) or count < 1):
        raise InvalidRule("count must be a positive whole number", param="rule")
    weekdays = tuple(sorted({WEEKDAYS.index(d) for d in data.get("weekdays", ()) if d in WEEKDAYS}))
    if len(weekdays) != len(set(data.get("weekdays", ()))) or (weekdays and freq != "weekly"):
        raise InvalidRule("weekdays are mon..sun and only apply to weekly rules", param="rule")
    until = timeparse.parse_date(data["until"], "until") if data.get("until") else None
    return Rule(freq=freq, interval=interval, until=until, count=count, weekdays=weekdays)


def rule_view(rule):
    if rule is None:
        return None
    return {"freq": rule.freq, "interval": rule.interval, "count": rule.count,
            "until": rule.until.isoformat() if rule.until else None,
            "weekdays": [WEEKDAYS[d] for d in rule.weekdays]}


class Events:
    def __init__(self, calendars, directory):
        self.calendars = calendars
        self.directory = directory
        self._events = {}

    def create(self, calendar, title, start, duration, attendees=(), rule=None, remind=()):
        self.calendars.get(calendar)
        if not isinstance(title, str) or not title.strip():
            raise InvalidTime("title must be a non-empty string", param="title")
        begin = timeparse.parse_dt(start, "start")
        length = timeparse.parse_duration(duration)
        for user in attendees:
            self.directory.get(user)
        if any(isinstance(m, bool) or not isinstance(m, int) or m < 0 for m in remind):
            raise InvalidTime("remind takes whole numbers of minutes", param="remind")
        event = Event(id=f"ev{len(self._events) + 1}", calendar=calendar, title=title.strip(), start=begin,
                      duration=length, attendees=tuple(attendees), rule=parse_rule(rule),
                      remind=tuple(sorted(set(remind))))
        self._events[event.id] = event
        return event

    def get(self, event_id):
        event = self._events.get(event_id)
        if event is None:
            raise UnknownEvent(f"no event {event_id!r}", param="event")
        return event

    def all(self, calendar=None, active_only=True):
        found = [e for e in self._events.values()
                 if calendar in (None, e.calendar) and (e.status == "active" or not active_only)]
        return sorted(found, key=lambda e: (e.start, e.id))

    def cancel(self, event_id):
        event = self.get(event_id)
        event.status = "cancelled"
        return event

    def skip(self, event_id, day):
        event = self.get(event_id)
        event.skips.add(timeparse.parse_date(day, "day"))
        return event

    def move(self, event_id, start):
        event = self.get(event_id)
        event.start = timeparse.parse_dt(start, "start")
        return event
