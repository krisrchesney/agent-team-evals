from datetime import timedelta

from . import recurrence, timeparse


class Reminders:
    def __init__(self, events):
        self.events = events

    def due(self, since, now):
        """Reminders that fire in (since, now], oldest first.

        An event with remind=(10, 60) fires 10 and 60 minutes (of elapsed time) before every occurrence.
        Times are shown in the zone of the event's calendar.
        """
        found = []
        for event in self.events.all():
            if not event.remind:
                continue
            zone = self.events.zone(event)
            reach = timedelta(minutes=max(event.remind))
            for start, _ in recurrence.expand(event, zone, since, now + reach + timedelta(minutes=1)):
                for minutes in event.remind:
                    fire = start - timedelta(minutes=minutes)
                    if since < fire <= now:
                        found.append((fire, event.id, minutes, start, event.title, zone))
        found.sort(key=lambda f: f[:3])
        return [{"event": eid, "title": title, "start": timeparse.fmt_dt(start, zone), "minutes": minutes,
                 "fire_at": timeparse.fmt_dt(fire, zone)} for fire, eid, minutes, start, title, zone in found]
