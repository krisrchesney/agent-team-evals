from dataclasses import dataclass

from .errors import InvalidTime, UnknownCalendar


@dataclass
class Calendar:
    id: str
    name: str


class Calendars:
    def __init__(self):
        self._calendars = {}

    def create(self, name):
        if not isinstance(name, str) or not name.strip():
            raise InvalidTime("calendar name must be a non-empty string", param="name")
        calendar = Calendar(id=f"cal{len(self._calendars) + 1}", name=name.strip())
        self._calendars[calendar.id] = calendar
        return calendar

    def get(self, calendar_id):
        calendar = self._calendars.get(calendar_id)
        if calendar is None:
            raise UnknownCalendar(f"no calendar {calendar_id!r}", param="calendar")
        return calendar

    def all(self):
        return sorted(self._calendars.values(), key=lambda c: c.id)
