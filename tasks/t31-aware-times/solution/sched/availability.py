from datetime import datetime, timedelta

from . import recurrence
from .timeparse import localize


class Availability:
    def __init__(self, directory, events):
        self.directory = directory
        self.events = events

    def busy(self, user_id, lo, hi):
        """(start, end) of the user's event occurrences overlapping [lo, hi), oldest first."""
        self.directory.get(user_id)
        spans = []
        for event in self.events.all():
            if user_id in event.attendees:
                spans.extend(recurrence.expand(event, self.events.zone(event), lo, hi))
        return sorted(spans)

    def is_free(self, user_id, start, end):
        return not self.busy(user_id, start, end)

    def window(self, user_id, day):
        """The user's working hours on their local date `day` as (start, end) instants, or None on a day off."""
        user = self.directory.get(user_id)
        hours = user.hours.get(day.weekday())
        if hours is None:
            return None
        return localize(datetime.combine(day, hours[0]), user.zone), localize(datetime.combine(day, hours[1]), user.zone)

    def within_hours(self, user_id, start, end):
        """True if [start, end] lies inside the working hours of the user's local day on which it starts."""
        window = self.window(user_id, start.astimezone(self.directory.get(user_id).zone).date())
        return window is not None and window[0] <= start and end <= window[1]

    def free_slots(self, users, day, duration, step=timedelta(minutes=30)):
        """Slots of `duration` inside everyone's working hours on `day` where nobody is busy.

        Each user's hours are those of the date `day` in their own zone. Candidate slots start where
        the shared window starts and then every `step`.
        """
        windows = [self.window(user, day) for user in users]
        if not windows or any(w is None for w in windows):
            return []
        begin = max(w[0] for w in windows)
        stop = min(w[1] for w in windows)
        slots = []
        start = begin
        while start + duration <= stop:
            if all(self.is_free(user, start, start + duration) for user in users):
                slots.append((start, start + duration))
            start += step
        return slots
