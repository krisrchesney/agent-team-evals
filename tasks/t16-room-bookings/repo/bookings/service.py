"""The booking service: the only place that changes state."""
from . import billing, permissions, rules
from .errors import InvalidRequest
from .fmt import money, slot
from .models import Booking


class BookingService:
    def __init__(self, store, clock, outbox):
        self.store = store
        self.clock = clock
        self.outbox = outbox

    def book(self, user_id, room_id, start, end, attendees):
        """Create one booking. Checks run in this order: unknown user, unknown room, permissions,
        time slot, attendees, lead time, room free, team budget."""
        user = self.store.user(user_id)
        room = self.store.room(room_id)
        permissions.check_can_book(user, room)
        rules.check_window(start, end)
        rules.check_attendees(room, attendees)
        rules.check_lead_time(self.clock.now(), start)
        rules.check_free(self.store, room.id, start, end)
        team = self.store.team(user.team)
        cost = billing.price(room, start, end)
        billing.charge(team, cost)
        booking = self.store.save(Booking(
            self.store.new_booking_id(), room.id, user.id, user.team, start, end, attendees, cost,
            created=self.clock.now()))
        self.outbox.send(user.id, f"Booked: {room.name}",
                         f"{slot(start, end)} for {attendees} attendees, {money(cost)}")
        return booking

    def cancel(self, user_id, booking_id):
        """Cancel a booking and give the whole cost back to the team."""
        user = self.store.user(user_id)
        booking = self.store.booking(booking_id)
        permissions.check_can_cancel(user, booking)
        if booking.status == "cancelled":
            raise InvalidRequest("booking is already cancelled")
        booking.status = "cancelled"
        billing.refund(self.store.team(booking.team), booking.cost_cents)
        room = self.store.room(booking.room_id)
        self.outbox.send(booking.user_id, f"Cancelled: {room.name}",
                         f"{slot(booking.start, booking.end)}, refund {money(booking.cost_cents)}")
        return booking

    def bookings_for_room(self, room_id, day):
        """Active bookings of the room that start on `day` (a date), earliest first."""
        self.store.room(room_id)
        return [b for b in self.store.active_for_room(room_id) if b.start.date() == day]
