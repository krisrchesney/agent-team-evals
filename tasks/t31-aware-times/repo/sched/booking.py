from . import timeparse
from .errors import Conflict


class Booking:
    def __init__(self, events, availability):
        self.events = events
        self.availability = availability

    def book(self, calendar, title, start, duration, attendees, remind=()):
        """Create an event if every attendee is free; returns (event, users outside their working hours)."""
        begin = timeparse.parse_dt(start, "start")
        end = begin + timeparse.parse_duration(duration)
        busy = [user for user in attendees if not self.availability.is_free(user, begin, end)]
        if busy:
            raise Conflict(f"busy: {', '.join(busy)}", param="attendees")
        event = self.events.create(calendar, title, start, duration, attendees=attendees, remind=remind)
        outside = [user for user in attendees if not self.availability.within_hours(user, begin, end)]
        return event, outside
