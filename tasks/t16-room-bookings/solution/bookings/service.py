"""The booking service: the only place that changes state."""
from datetime import timedelta

from . import billing, permissions, rules
from .errors import BookingError, Conflict, InvalidRequest
from .fmt import money, slot
from .models import Booking, WaitlistEntry

SERIES_GAPS = {"weekly": timedelta(days=7), "biweekly": timedelta(days=14)}
SERIES_MIN, SERIES_MAX = 2, 12


class BookingService:
    def __init__(self, store, clock, outbox):
        self.store = store
        self.clock = clock
        self.outbox = outbox

    # -- booking -------------------------------------------------------------------------

    def _check_slot(self, room, start, end, attendees):
        rules.check_window(start, end)
        rules.check_attendees(room, attendees)
        rules.check_lead_time(self.clock.now(), start)

    def _create(self, user, room, start, end, attendees, cost, series_id=None):
        return self.store.save(Booking(
            self.store.new_booking_id(), room.id, user.id, user.team, start, end, attendees, cost,
            created=self.clock.now(), series_id=series_id))

    def _booked_message(self, subject_prefix, user, room, booking):
        self.outbox.send(user.id, f"{subject_prefix}: {room.name}",
                         f"{slot(booking.start, booking.end)} for {booking.attendees} attendees, "
                         f"{money(booking.cost_cents)}")

    def book(self, user_id, room_id, start, end, attendees, waitlist=False):
        """Create one booking. Checks run in this order: unknown user, unknown room, permissions,
        time slot, attendees, lead time, room free, team budget. With `waitlist=True`, a taken room
        puts the request on the waitlist instead and returns the WaitlistEntry."""
        user = self.store.user(user_id)
        room = self.store.room(room_id)
        permissions.check_can_book(user, room)
        self._check_slot(room, start, end, attendees)
        try:
            rules.check_free(self.store, room.id, start, end)
        except Conflict:
            if not waitlist:
                raise
            return self._enqueue(user, room, start, end, attendees)
        team = self.store.team(user.team)
        cost = billing.price(room, start, end)
        billing.charge(team, cost)
        booking = self._create(user, room, start, end, attendees, cost)
        self._booked_message("Booked", user, room, booking)
        return booking

    def book_series(self, user_id, room_id, start, end, attendees, repeat, count):
        """Book `count` repeats of a slot, all or nothing. Returns the bookings in time order."""
        user = self.store.user(user_id)
        room = self.store.room(room_id)
        if repeat not in SERIES_GAPS:
            raise InvalidRequest("repeat must be 'weekly' or 'biweekly'")
        if type(count) is not int or not SERIES_MIN <= count <= SERIES_MAX:
            raise InvalidRequest(f"count must be between {SERIES_MIN} and {SERIES_MAX}")
        permissions.check_can_book(user, room, series=True)
        gap = SERIES_GAPS[repeat]
        slots = [(start + gap * i, end + gap * i) for i in range(count)]
        for number, (s, e) in enumerate(slots, start=1):
            try:
                self._check_slot(room, s, e, attendees)
                rules.check_free(self.store, room.id, s, e)
            except BookingError as err:
                raise type(err)(f"occurrence {number}: {err}") from None
        team = self.store.team(user.team)
        costs = [billing.series_price(billing.price(room, s, e), count) for s, e in slots]
        total = sum(costs)
        billing.charge(team, total)
        series_id = self.store.new_series_id()
        made = [self._create(user, room, s, e, attendees, c, series_id) for (s, e), c in zip(slots, costs)]
        self.outbox.send(user.id, f"Series booked: {room.name}",
                         f"{count} bookings of {room.name}, first {slot(*slots[0])}, total {money(total)}")
        return made

    # -- cancelling ----------------------------------------------------------------------

    def cancel(self, user_id, booking_id, series=False):
        """Cancel a booking; the team gets back the cost minus the cancellation fee.

        With `series=True` on a series booking this and every later active occurrence is
        cancelled and a list is returned; otherwise the one Booking is returned (or a one-item
        list when `series=True` was given for a booking that is not in a series).
        """
        user = self.store.user(user_id)
        booking = self.store.booking(booking_id)
        permissions.check_can_cancel(user, booking)
        if booking.status == "cancelled":
            raise InvalidRequest("booking is already cancelled")
        now = self.clock.now()
        if booking.start <= now:
            raise InvalidRequest("booking has already started")
        whole_series = series and booking.series_id is not None
        targets = [booking]
        if whole_series:
            targets = [b for b in self.store.series(booking.series_id)
                       if b.status == "active" and b.start >= booking.start]
        team = self.store.team(booking.team)
        room = self.store.room(booking.room_id)
        refunded = fees = 0
        for target in targets:
            fee = billing.cancellation_fee(target.cost_cents, target.start, now)
            target.status = "cancelled"
            billing.settle_cancellation(team, target.cost_cents, fee)
            refunded += target.cost_cents - fee
            fees += fee
        if whole_series:
            self.outbox.send(booking.user_id, f"Series cancelled: {room.name}",
                             f"{len(targets)} bookings cancelled, refund {money(refunded)}, fee {money(fees)}")
        else:
            body = f"{slot(booking.start, booking.end)}, refund {money(refunded)}"
            if fees:
                body += f", fee {money(fees)}"
            self.outbox.send(booking.user_id, f"Cancelled: {room.name}", body)
        self._promote(room.id)
        return targets if series else booking

    # -- waitlist ------------------------------------------------------------------------

    def _enqueue(self, user, room, start, end, attendees):
        entry = self.store.add_waiting(WaitlistEntry(
            self.store.new_waitlist_id(), user.id, room.id, start, end, attendees, self.clock.now()))
        self.outbox.send(user.id, f"Waitlisted: {room.name}",
                         f"{slot(start, end)} for {attendees} attendees")
        return entry

    def leave_waitlist(self, user_id, entry_id):
        user = self.store.user(user_id)
        entry = self.store.waiting_entry(entry_id)
        permissions.check_can_leave(user, entry)
        del self.store.waitlist[entry.id]

    def _promote(self, room_id):
        """Book waiting requests that now fit, first come first served."""
        room = self.store.room(room_id)
        for entry in self.store.waiting_for_room(room_id):
            if entry.start - self.clock.now() < rules.LEAD_TIME:
                del self.store.waitlist[entry.id]
                continue
            if rules.find_conflict(self.store, room_id, entry.start, entry.end):
                continue
            user = self.store.user(entry.user_id)
            team = self.store.team(user.team)
            cost = billing.price(room, entry.start, entry.end)
            if cost > team.budget_cents:
                continue
            billing.charge(team, cost)
            booking = self._create(user, room, entry.start, entry.end, entry.attendees, cost)
            del self.store.waitlist[entry.id]
            self._booked_message("Booked from waitlist", user, room, booking)

    # -- queries -------------------------------------------------------------------------

    def bookings_for_room(self, room_id, day):
        """Active bookings of the room that start on `day` (a date), earliest first."""
        self.store.room(room_id)
        return [b for b in self.store.active_for_room(room_id) if b.start.date() == day]
