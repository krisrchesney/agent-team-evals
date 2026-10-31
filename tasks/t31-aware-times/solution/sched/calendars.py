from dataclasses import dataclass

from . import timeparse
from .errors import InvalidTime, UnknownCalendar


@dataclass
class Calendar:
    id: str
    name: str
    tz: str = "UTC"

    @property
    def zone(self):
        return timeparse.get_zone(self.tz)


class Calendars:
    def __init__(self):
        self._calendars = {}

    def create(self, name, tz="UTC"):
        if not isinstance(name, str) or not name.strip():
            raise InvalidTime("calendar name must be a non-empty string", param="name")
        timeparse.get_zone(tz)
        calendar = Calendar(id=f"cal{len(self._calendars) + 1}", name=name.strip(), tz=tz)
        self._calendars[calendar.id] = calendar
        return calendar

    def get(self, calendar_id):
        calendar = self._calendars.get(calendar_id)
        if calendar is None:
            raise UnknownCalendar(f"no calendar {calendar_id!r}", param="calendar")
        return calendar

    def all(self):
        return sorted(self._calendars.values(), key=lambda c: c.id)
