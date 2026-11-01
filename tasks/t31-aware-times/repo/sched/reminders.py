from datetime import timedelta

from . import recurrence, timeparse


class Reminders:
    def __init__(self, events):
        self.events = events

    def due(self, since, now):
        """Reminders that fire in (since, now], oldest first.

        An event with remind=(10, 60) fires 10 and 60 minutes before every occurrence.
        """
        found = []
        for event in self.events.all():
            if not event.remind:
                continue
            reach = timedelta(minutes=max(event.remind))
            for start, _ in recurrence.expand(event, since, now + reach + timedelta(minutes=1)):
                for minutes in event.remind:
                    fire = start - timedelta(minutes=minutes)
                    if since < fire <= now:
                        found.append((fire, event.id, minutes, start, event.title))
        found.sort(key=lambda f: f[:3])
        return [{"event": eid, "title": title, "start": timeparse.fmt_dt(start), "minutes": minutes,
                 "fire_at": timeparse.fmt_dt(fire)} for fire, eid, minutes, start, title in found]
