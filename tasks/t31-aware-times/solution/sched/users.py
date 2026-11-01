from dataclasses import dataclass

from . import timeparse
from .errors import DuplicateUser, InvalidTime, UnknownUser

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DEFAULT_HOURS = {day: ("09:00", "17:00") for day in WEEKDAYS[:5]}


@dataclass
class User:
    id: str
    name: str
    hours: dict          # weekday number (Monday is 0) -> (start, end) local times; a missing day is a day off
    tz: str = "UTC"

    @property
    def zone(self):
        return timeparse.get_zone(self.tz)

    def hours_view(self):
        return {WEEKDAYS[d]: [timeparse.fmt_time(s), timeparse.fmt_time(e)] for d, (s, e) in sorted(self.hours.items())}


class Directory:
    def __init__(self):
        self._users = {}

    def add(self, user_id, name, hours=None, tz="UTC"):
        if not isinstance(user_id, str) or not user_id.strip():
            raise InvalidTime("user id must be a non-empty string", param="user")
        if user_id in self._users:
            raise DuplicateUser(f"user {user_id} already exists", param="user")
        timeparse.get_zone(tz)
        parsed = {}
        for day, span in (DEFAULT_HOURS if hours is None else hours).items():
            if day not in WEEKDAYS:
                raise InvalidTime(f"hours are keyed by {', '.join(WEEKDAYS)}", param="hours")
            start, end = (timeparse.parse_time(part, "hours") for part in span)
            if start >= end:
                raise InvalidTime("working hours must end after they start", param="hours")
            parsed[WEEKDAYS.index(day)] = (start, end)
        user = User(id=user_id, name=name, hours=parsed, tz=tz)
        self._users[user_id] = user
        return user

    def get(self, user_id):
        user = self._users.get(user_id)
        if user is None:
            raise UnknownUser(f"no user {user_id!r}", param="user")
        return user

    def all(self):
        return sorted(self._users.values(), key=lambda u: u.id)
