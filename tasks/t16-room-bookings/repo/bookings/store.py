"""In-memory storage for rooms, users, teams and bookings."""
from .errors import NotFound
from .models import Team


class Store:
    def __init__(self):
        self.rooms = {}
        self.users = {}
        self.teams = {}
        self.bookings = {}
        self._next_booking = 1

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

    def save(self, booking):
        self.bookings[booking.id] = booking
        return booking

    def active_for_room(self, room_id):
        """Active bookings of a room, earliest first."""
        found = [b for b in self.bookings.values() if b.room_id == room_id and b.status == "active"]
        return sorted(found, key=lambda b: (b.start, b.id))
