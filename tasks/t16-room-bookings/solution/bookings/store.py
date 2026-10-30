"""In-memory storage for rooms, users, teams, bookings and the waitlist."""
from .errors import NotFound
from .models import Team


class Store:
    def __init__(self):
        self.rooms = {}
        self.users = {}
        self.teams = {}
        self.bookings = {}
        self.waitlist = {}
        self._next_booking = 1
        self._next_series = 1
        self._next_waitlist = 1

    def add_room(self, room):
        self.rooms[room.id] = room
        return room

    def add_user(self, user):
        self.users[user.id] = user
        return user

    def add_team(self, name, budget_cents):
        self.teams[name] = Team(name, budget_cents)
        return self.teams[name]

    def room(self, room_id):
        if room_id not in self.rooms:
            raise NotFound(f"unknown room '{room_id}'")
        return self.rooms[room_id]

    def user(self, user_id):
        if user_id not in self.users:
            raise NotFound(f"unknown user '{user_id}'")
        return self.users[user_id]

    def team(self, name):
        if name not in self.teams:
            raise NotFound(f"unknown team '{name}'")
        return self.teams[name]

    def booking(self, booking_id):
        if booking_id not in self.bookings:
            raise NotFound(f"unknown booking {booking_id}")
        return self.bookings[booking_id]

    def new_booking_id(self):
        booking_id = self._next_booking
        self._next_booking += 1
        return booking_id

    def new_series_id(self):
        series_id = self._next_series
        self._next_series += 1
        return series_id

    def save(self, booking):
        self.bookings[booking.id] = booking
        return booking

    def active_for_room(self, room_id):
        """Active bookings of a room, earliest first."""
        found = [b for b in self.bookings.values() if b.room_id == room_id and b.status == "active"]
        return sorted(found, key=lambda b: (b.start, b.id))

    def series(self, series_id):
        """All bookings of a series, earliest first, whatever their status."""
        found = [b for b in self.bookings.values() if b.series_id == series_id]
        return sorted(found, key=lambda b: (b.start, b.id))

    def new_waitlist_id(self):
        entry_id = self._next_waitlist
        self._next_waitlist += 1
        return entry_id

    def add_waiting(self, entry):
        self.waitlist[entry.id] = entry
        return entry

    def waiting_entry(self, entry_id):
        if entry_id not in self.waitlist:
            raise NotFound(f"unknown waitlist entry {entry_id}")
        return self.waitlist[entry_id]

    def waiting_for_room(self, room_id):
        """Waitlist entries of a room, first come first."""
        found = [e for e in self.waitlist.values() if e.room_id == room_id]
        return sorted(found, key=lambda e: (e.created, e.id))
