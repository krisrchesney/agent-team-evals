from datetime import datetime, time, timedelta

from . import recurrence, timeparse


class Agenda:
    def __init__(self, directory, events):
        self.directory = directory
        self.events = events

    def day(self, user_id, day):
        """The user's occurrences that overlap `day`, oldest first."""
        self.directory.get(user_id)
        lo = datetime.combine(day, time(0, 0))
        hi = lo + timedelta(days=1)
        found = []
        for event in self.events.all():
            if user_id in event.attendees:
                for start, end in recurrence.expand(event, lo, hi):
                    found.append((start, end, event))
        found.sort(key=lambda f: (f[0], f[2].id))
        return [{"event": e.id, "title": e.title, "start": timeparse.fmt_dt(s), "end": timeparse.fmt_dt(en)}
                for s, en, e in found]

    def week(self, user_id, first_day):
        return {(first_day + timedelta(days=i)).isoformat(): self.day(user_id, first_day + timedelta(days=i))
                for i in range(7)}

    def digest(self, user_id, day):
        """A short text agenda: a heading, then one 'HH:MM-HH:MM Title' line per occurrence."""
        user = self.directory.get(user_id)
        lines = [f"{user.name} - {day:%a %d %b}"]
        found = self.day(user_id, day)
        for item in found:
            start = timeparse.parse_dt(item["start"])
            end = timeparse.parse_dt(item["end"])
            lines.append(f"{timeparse.fmt_clock(start)}-{timeparse.fmt_clock(end)} {item['title']}")
        if not found:
            lines.append("No events.")
        return "\n".join(lines)
