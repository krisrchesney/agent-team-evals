from datetime import timedelta

from . import ics, snapshot, timeparse
from .agenda import Agenda
from .availability import Availability
from .booking import Booking
from .calendars import Calendars
from .clock import SystemClock
from .events import Events, rule_view
from .recurrence import expand
from .reminders import Reminders
from .users import Directory


class Scheduler:
    def __init__(self, clock=None):
        self.clock = clock or SystemClock()
        self.directory = Directory()
        self.calendars = Calendars()
        self.events = Events(self.calendars, self.directory)
        self.reminders = Reminders(self.events)
        self.availability = Availability(self.directory, self.events)
        self.booking = Booking(self.events, self.availability)
        self.agenda = Agenda(self.directory, self.events)

    def _now(self):
        return self.clock.now().astimezone(timeparse.UTC)

    # views

    def event_view(self, event):
        zone = self.events.zone(event)
        return {"id": event.id, "calendar": event.calendar, "title": event.title,
                "start": timeparse.fmt_dt(event.start, zone),
                "end": timeparse.fmt_dt(event.start + event.duration, zone),
                "duration": timeparse.fmt_duration(event.duration), "attendees": list(event.attendees),
                "rule": rule_view(event.rule), "skips": sorted(d.isoformat() for d in event.skips),
                "status": event.status, "remind": list(event.remind)}

    # users and calendars

    def add_user(self, user_id, name, hours=None, tz="UTC"):
        user = self.directory.add(user_id, name, hours, tz)
        return {"id": user.id, "name": user.name, "tz": user.tz, "hours": user.hours_view()}

    def create_calendar(self, name, tz="UTC"):
        calendar = self.calendars.create(name, tz)
        return {"id": calendar.id, "name": calendar.name, "tz": calendar.tz}

    # events

    def create_event(self, calendar, title, start, duration, attendees=(), rule=None, remind=()):
        return self.event_view(self.events.create(calendar, title, start, duration, attendees, rule, remind))

    def get_event(self, event_id):
        return self.event_view(self.events.get(event_id))

    def cancel_event(self, event_id):
        return self.event_view(self.events.cancel(event_id))

    def skip_occurrence(self, event_id, day):
        return self.event_view(self.events.skip(event_id, day))

    def move_event(self, event_id, start):
        return self.event_view(self.events.move(event_id, start))

    def occurrences(self, event_id, start, end):
        event = self.events.get(event_id)
        zone = self.events.zone(event)
        found = expand(event, zone, timeparse.parse_dt(start, zone, "start"), timeparse.parse_dt(end, zone, "end"))
        return [{"start": timeparse.fmt_dt(s, zone), "end": timeparse.fmt_dt(e, zone)} for s, e in found]

    # reminders, availability, booking

    def reminders_due(self, since):
        return self.reminders.due(timeparse.parse_dt(since, timeparse.UTC, "since"), self._now())

    def free_slots(self, users, day, duration, step=30, tz="UTC"):
        zone = timeparse.get_zone(tz)
        slots = self.availability.free_slots(users, timeparse.parse_date(day), timeparse.parse_duration(duration),
                                             timedelta(minutes=step))
        return [{"start": timeparse.fmt_dt(s, zone), "end": timeparse.fmt_dt(e, zone)} for s, e in slots]

    def book(self, calendar, title, start, duration, attendees, remind=()):
        event, outside = self.booking.book(calendar, title, start, duration, attendees, remind)
        return {**self.event_view(event), "outside_hours": outside}

    # agenda

    def agenda_for(self, user_id, day):
        return self.agenda.day(user_id, timeparse.parse_date(day))

    def week_for(self, user_id, first_day):
        return self.agenda.week(user_id, timeparse.parse_date(first_day))

    def digest(self, user_id, day):
        return self.agenda.digest(user_id, timeparse.parse_date(day))

    # export and persistence

    def export_ics(self, calendar_id):
        calendar = self.calendars.get(calendar_id)
        return ics.export(calendar, self.events.all(calendar_id), self._now())

    def dump(self):
        return snapshot.dump(self.directory, self.calendars, self.events)

    @classmethod
    def load(cls, data, clock=None):
        sched = cls(clock)
        snapshot.load(data, sched)
        return sched
