from datetime import datetime, time, timedelta

from . import recurrence, timeparse
from .timeparse import localize


class Agenda:
    def __init__(self, directory, events):
        self.directory = directory
        self.events = events

    def _day(self, user, day):
        """(start, end, event) for the user's occurrences that overlap their local date `day`."""
        zone = user.zone
        lo = localize(datetime.combine(day, time(0, 0)), zone)
        hi = localize(datetime.combine(day + timedelta(days=1), time(0, 0)), zone)
        found = []
        for event in self.events.all():
            if user.id in event.attendees:
                for start, end in recurrence.expand(event, self.events.zone(event), lo, hi):
                    found.append((start, end, event))
        found.sort(key=lambda f: (f[0], f[2].id))
        return found

    def day(self, user_id, day):
        """The user's occurrences that overlap their local date `day`, oldest first, in their zone."""
        user = self.directory.get(user_id)
        return [{"event": e.id, "title": e.title, "start": timeparse.fmt_dt(s, user.zone),
                 "end": timeparse.fmt_dt(en, user.zone)} for s, en, e in self._day(user, day)]

    def week(self, user_id, first_day):
        return {(first_day + timedelta(days=i)).isoformat(): self.day(user_id, first_day + timedelta(days=i))
                for i in range(7)}

    def digest(self, user_id, day):
        """A short text agenda in the user's local time: a heading, then 'HH:MM-HH:MM Title' lines."""
        user = self.directory.get(user_id)
        lines = [f"{user.name} - {day:%a %d %b}"]
        found = self._day(user, day)
        for start, end, event in found:
            lines.append(f"{timeparse.fmt_clock(start, user.zone)}-{timeparse.fmt_clock(end, user.zone)} {event.title}")
        if not found:
            lines.append("No events.")
        return "\n".join(lines)
