import unittest
from datetime import date, datetime, timedelta

from bookings import (Booking, BookingService, Clock, Conflict, InsufficientBudget, InvalidRequest, NotAllowed,
                      NotFound, Outbox, Room, Store, Team, User)
from bookings.fmt import money, slot
from bookings.report import agenda, spend_report, utilization


def entry_cls():
    from bookings.models import WaitlistEntry  # imported late so that the other tests still run without it
    return WaitlistEntry


def waitlist_report(store):
    from bookings.report import waitlist_report as report
    return report(store)


def D(day, hour=10, minute=0):
    """A time in June 2024 (the 3rd is a Monday)."""
    return datetime(2024, 6, day, hour, minute)


class Base(unittest.TestCase):
    def setUp(self):
        s = self.store = Store()
        s.add_room(Room("r1", "Boardroom", 10, 6000))
        s.add_room(Room("r2", "Atrium", 6, 4000, "premium"))
        s.add_room(Room("r3", "Cheap", 10, 1001))  # 30 minutes cost 501 (500.5 rounded up)
        s.add_room(Room("r4", "Half", 10, 1010))  # 30 minutes cost 505
        s.add_room(Room("r5", "Grand", 10, 123456))
        for team, budget in (("ops", 1_000_000), ("tiny", 6000), ("rich", 100_000_000),
                             ("exact", 21600), ("short", 21599)):
            s.add_team(team, budget)
        for uid, role, team in (("ann", "manager", "ops"), ("bob", "staff", "ops"), ("cat", "staff", "ops"),
                                ("gus", "guest", "ops"), ("dan", "admin", "rich"), ("fay", "staff", "tiny"),
                                ("hal", "staff", "tiny"), ("ivy", "manager", "tiny"), ("rex", "manager", "rich"),
                                ("zed", "manager", "exact"), ("yan", "manager", "short")):
            s.add_user(User(uid, uid.title(), role, team))
        self.clock = Clock(D(3, 8, 0))
        self.outbox = Outbox()
        self.svc = BookingService(s, self.clock, self.outbox)

    def book(self, user, room, start, hours=1, attendees=2, **kw):
        return self.svc.book(user, room, start, start + timedelta(hours=hours), attendees, **kw)

    def series(self, user, room, start, count, repeat="weekly", hours=1, attendees=2):
        return self.svc.book_series(user, room, start, start + timedelta(hours=hours), attendees, repeat, count)

    def messages(self, user=None):
        return [(m.subject, m.body) for m in self.outbox.messages if user is None or m.user_id == user]

    def team(self, name):
        return self.store.teams[name]


class HiddenBookings(Base):
    # R1: behaviour that exists today

    def test_r1_booking_message_and_cost(self):
        b = self.book("bob", "r1", D(4, 9), hours=1.5, attendees=4)
        self.assertEqual(b.cost_cents, 9000)
        self.assertEqual(self.messages("bob"), [("Booked: Boardroom", "Tue 04 Jun 09:00-10:30 for 4 attendees, $90.00")])

    def test_r1_one_attendee_is_still_plural(self):
        self.book("bob", "r1", D(4, 9), attendees=1)
        self.assertEqual(self.messages()[0][1], "Tue 04 Jun 09:00-10:00 for 1 attendees, $60.00")

    def test_r1_cost_rounds_half_up(self):
        b = self.svc.book("bob", "r3", D(4, 9), D(4, 9, 30), 2)
        self.assertEqual(b.cost_cents, 501)

    def test_r1_touching_bookings_do_not_conflict(self):
        self.book("bob", "r1", D(4, 9))
        self.book("cat", "r1", D(4, 10))
        with self.assertRaises(Conflict) as ctx:
            self.book("cat", "r1", D(4, 9, 30), hours=1)
        self.assertEqual(str(ctx.exception), "room is already booked from 09:00 to 10:00")

    def test_r1_check_order_and_messages(self):
        with self.assertRaises(NotFound) as ctx:
            self.book("nobody", "r1", D(4, 9))
        self.assertEqual(str(ctx.exception), "unknown user 'nobody'")
        with self.assertRaises(NotFound) as ctx:
            self.book("bob", "r9", D(4, 9))
        self.assertEqual(str(ctx.exception), "unknown room 'r9'")
        with self.assertRaises(NotAllowed) as ctx:
            self.book("gus", "r1", D(4, 9))
        self.assertEqual(str(ctx.exception), "guests cannot book rooms")
        with self.assertRaises(NotAllowed) as ctx:
            self.book("bob", "r2", D(4, 9))
        self.assertEqual(str(ctx.exception), "premium rooms need a manager")
        with self.assertRaises(InvalidRequest) as ctx:
            self.book("bob", "r1", D(4, 9), attendees=11)
        self.assertEqual(str(ctx.exception), "attendees must be between 1 and 10")
        with self.assertRaises(InsufficientBudget) as ctx:
            self.book("fay", "r1", D(4, 9), hours=2)
        self.assertEqual(str(ctx.exception), "team budget too low: need $120.00, have $60.00")

    def test_r1_cancel_permissions(self):
        b = self.book("bob", "r1", D(5, 9))
        with self.assertRaises(NotAllowed) as ctx:
            self.svc.cancel("cat", b.id)
        self.assertEqual(str(ctx.exception), "you cannot cancel this booking")
        self.svc.cancel("ann", b.id)  # a manager of the same team
        c = self.book("bob", "r1", D(5, 11))
        self.svc.cancel("dan", c.id)  # an admin
        with self.assertRaises(NotAllowed):
            self.svc.cancel("ivy", self.book("bob", "r1", D(5, 13)).id)  # manager of another team

    def test_r1_early_cancel_refunds_everything(self):
        b = self.book("bob", "r1", D(5, 9))
        cancelled = self.svc.cancel("bob", b.id)
        self.assertEqual(cancelled.status, "cancelled")
        self.assertEqual((self.team("ops").budget_cents, self.team("ops").spent_cents), (1_000_000, 0))
        self.assertEqual(self.messages("bob")[-1], ("Cancelled: Boardroom", "Wed 05 Jun 09:00-10:00, refund $60.00"))

    def test_r1_already_cancelled(self):
        b = self.book("bob", "r1", D(5, 9))
        self.svc.cancel("bob", b.id)
        with self.assertRaises(InvalidRequest) as ctx:
            self.svc.cancel("bob", b.id)
        self.assertEqual(str(ctx.exception), "booking is already cancelled")

    def test_r1_old_constructors_and_reports(self):
        b = Booking(1, "r1", "bob", "ops", D(4, 9), D(4, 10), 2, 100)
        self.assertIsNone(b.series_id)
        self.assertEqual(Team("x", 5).fees_cents, 0)
        self.book("bob", "r1", D(4, 9), hours=1.5)
        self.assertEqual(utilization(self.store, date(2024, 6, 3), date(2024, 6, 7)).splitlines()[1],
                         "Boardroom" + " " * 10 + "3.0%  1.5h")
        self.assertEqual(agenda(self.store, date(2024, 6, 4)), "09:00-10:30 Boardroom (Bob, 2 people)")

    # R2: book_series basics

    def test_r2_weekly_and_biweekly_dates(self):
        weekly = self.series("ann", "r1", D(4), 3)
        self.assertEqual([b.start for b in weekly], [D(4), D(11), D(18)])
        self.assertEqual([b.end for b in weekly], [D(4, 11), D(11, 11), D(18, 11)])
        biweekly = self.series("ann", "r1", D(5), 3, repeat="biweekly")
        self.assertEqual([b.start for b in biweekly], [D(5), D(19), datetime(2024, 7, 3, 10, 0)])

    def test_r2_returns_bookings_that_are_stored(self):
        made = self.series("ann", "r1", D(4), 2)
        self.assertTrue(all(isinstance(b, Booking) for b in made))
        self.assertEqual([self.store.bookings[b.id] for b in made], made)
        self.assertEqual({(b.user_id, b.team, b.room_id, b.attendees, b.status) for b in made},
                         {("ann", "ops", "r1", 2, "active")})

    def test_r2_admin_and_manager_in_premium(self):
        self.assertEqual(len(self.series("rex", "r2", D(4), 2)), 2)
        self.assertEqual(len(self.series("dan", "r1", D(5), 2)), 2)

    # R3: argument validation

    def test_r3_bad_repeat(self):
        for bad in ("daily", "monthly", "Weekly", None):
            with self.assertRaises(InvalidRequest) as ctx:
                self.series("ann", "r1", D(4), 3, repeat=bad)
            self.assertEqual(str(ctx.exception), "repeat must be 'weekly' or 'biweekly'")

    def test_r3_bad_count(self):
        for bad in (0, 1, 13, 100, -2, "3", 2.0, None):
            with self.assertRaises(InvalidRequest) as ctx:
                self.series("ann", "r1", D(4), bad)
            self.assertEqual(str(ctx.exception), "count must be between 2 and 12")

    def test_r3_count_limits_are_inclusive(self):
        self.assertEqual(len(self.series("rex", "r1", D(4), 2)), 2)
        self.assertEqual(len(self.series("rex", "r1", D(5), 12)), 12)

    def test_r3_order_of_checks(self):
        with self.assertRaises(NotFound):
            self.series("nobody", "r1", D(4), 1, repeat="daily")
        with self.assertRaises(NotFound):
            self.series("ann", "r9", D(4), 1, repeat="daily")
        with self.assertRaises(InvalidRequest) as ctx:  # repeat before count
            self.series("ann", "r1", D(4), 1, repeat="daily")
        self.assertEqual(str(ctx.exception), "repeat must be 'weekly' or 'biweekly'")
        with self.assertRaises(InvalidRequest):  # validation before permissions
            self.series("gus", "r1", D(4), 1)
        with self.assertRaises(InvalidRequest):
            self.series("bob", "r1", D(4), 1)

    # R4: who may book a series

    def test_r4_guest_staff_and_premium(self):
        with self.assertRaises(NotAllowed) as ctx:
            self.series("gus", "r1", D(4), 3)
        self.assertEqual(str(ctx.exception), "guests cannot book rooms")
        with self.assertRaises(NotAllowed) as ctx:
            self.series("bob", "r1", D(4), 3)
        self.assertEqual(str(ctx.exception), "only managers can book series")
        with self.assertRaises(NotAllowed) as ctx:  # staff and premium: the series rule is reported first
            self.series("bob", "r2", D(4), 3)
        self.assertEqual(str(ctx.exception), "only managers can book series")

    # R5: occurrence checks

    def test_r5_conflict_names_the_occurrence(self):
        self.svc.book("bob", "r1", D(18, 10, 30), D(18, 11, 30), 2)
        with self.assertRaises(Conflict) as ctx:
            self.series("ann", "r1", D(4), 4)
        self.assertEqual(str(ctx.exception), "occurrence 3: room is already booked from 10:30 to 11:30")

    def test_r5_first_failing_occurrence_wins(self):
        self.svc.book("bob", "r1", D(11, 10), D(11, 11), 2)
        self.svc.book("cat", "r1", D(25, 10), D(25, 11), 2)
        with self.assertRaises(Conflict) as ctx:
            self.series("ann", "r1", D(4), 4)
        self.assertTrue(str(ctx.exception).startswith("occurrence 2: "))

    def test_r5_slot_attendees_and_lead_time_are_checked_in_order(self):
        with self.assertRaises(InvalidRequest) as ctx:
            self.series("ann", "r1", D(4, 7), 3)
        self.assertEqual(str(ctx.exception), "occurrence 1: bookings must be on weekdays between 08:00 and 18:00")
        with self.assertRaises(InvalidRequest) as ctx:
            self.series("ann", "r1", D(4), 3, attendees=11)
        self.assertEqual(str(ctx.exception), "occurrence 1: attendees must be between 1 and 10")
        self.clock.set(D(4, 9, 50))
        with self.assertRaises(InvalidRequest) as ctx:
            self.series("ann", "r1", D(4), 3)
        self.assertEqual(str(ctx.exception), "occurrence 1: bookings must start at least 15 minutes from now")
        with self.assertRaises(InvalidRequest) as ctx:
            self.series("ann", "r1", D(4), 3, attendees=0)
        self.assertEqual(str(ctx.exception), "occurrence 1: attendees must be between 1 and 10")

    def test_r5_bad_slot_message_keeps_its_text(self):
        with self.assertRaises(InvalidRequest) as ctx:
            self.svc.book_series("ann", "r1", D(4, 9), D(4, 9, 10), 2, "weekly", 3)
        self.assertEqual(str(ctx.exception), "occurrence 1: times must be on 15-minute marks")

    # R6: all or nothing

    def test_r6_failure_changes_nothing(self):
        self.svc.book("bob", "r1", D(18, 10), D(18, 11), 2)
        bookings, budget = dict(self.store.bookings), self.team("ops").budget_cents
        sent = len(self.outbox.messages)
        with self.assertRaises(Conflict):
            self.series("ann", "r1", D(4), 4)
        self.assertEqual(self.store.bookings, bookings)
        self.assertEqual((self.team("ops").budget_cents, self.team("ops").spent_cents), (budget, 6000))
        self.assertEqual(len(self.outbox.messages), sent)

    def test_r6_failed_budget_changes_nothing(self):
        with self.assertRaises(InsufficientBudget):
            self.series("yan", "r1", D(4), 4)
        self.assertEqual(self.store.bookings, {})
        self.assertEqual(self.outbox.messages, [])
        self.assertEqual(self.team("short").budget_cents, 21599)

    def test_r6_failed_series_leave_ids_alone(self):
        with self.assertRaises(InsufficientBudget):
            self.series("yan", "r1", D(4), 4)
        made = self.series("ann", "r1", D(4), 2)
        self.assertEqual([b.id for b in made], [1, 2])
        self.assertEqual([b.series_id for b in made], [1, 1])

    # R7: series_id

    def test_r7_series_ids(self):
        single = self.book("bob", "r1", D(6, 9))
        first = self.series("ann", "r1", D(4), 2)
        second = self.series("ann", "r1", D(5), 3)
        self.assertIsNone(single.series_id)
        self.assertEqual([b.series_id for b in first], [1, 1])
        self.assertEqual([b.series_id for b in second], [2, 2, 2])
        self.assertEqual([b.id for b in first + second], [2, 3, 4, 5, 6])

    def test_r7_later_single_booking_has_no_series(self):
        self.series("ann", "r1", D(4), 2)
        self.assertIsNone(self.book("bob", "r1", D(6, 9)).series_id)

    # R8: discount

    def test_r8_no_discount_below_four(self):
        self.assertEqual([b.cost_cents for b in self.series("ann", "r1", D(4), 3)], [6000] * 3)

    def test_r8_discount_from_four(self):
        self.assertEqual([b.cost_cents for b in self.series("ann", "r1", D(4), 4)], [5400] * 4)
        self.assertEqual([b.cost_cents for b in self.series("ann", "r1", D(5), 12)], [5400] * 12)

    def test_r8_discount_rounds_half_up_per_occurrence(self):
        made = self.svc.book_series("ann", "r4", D(4, 9), D(4, 9, 30), 2, "weekly", 4)
        self.assertEqual([b.cost_cents for b in made], [455] * 4)  # 505 * 0.9 = 454.5
        made = self.svc.book_series("ann", "r3", D(4, 9), D(4, 9, 30), 2, "weekly", 4)
        self.assertEqual([b.cost_cents for b in made], [451] * 4)  # 501 * 0.9 = 450.9

    def test_r8_biweekly_gets_the_same_discount(self):
        self.assertEqual({b.cost_cents for b in self.series("ann", "r1", D(4), 5, repeat="biweekly")}, {5400})

    # R9: series budget

    def test_r9_charged_once_with_the_total(self):
        self.series("ann", "r1", D(4), 4)
        self.assertEqual((self.team("ops").budget_cents, self.team("ops").spent_cents), (1_000_000 - 21600, 21600))

    def test_r9_exact_budget_is_enough(self):
        self.series("zed", "r1", D(4), 4)
        self.assertEqual(self.team("exact").budget_cents, 0)

    def test_r9_one_cent_short(self):
        with self.assertRaises(InsufficientBudget) as ctx:
            self.series("yan", "r1", D(4), 4)
        self.assertEqual(str(ctx.exception), "team budget too low: need $216.00, have $215.99")

    def test_r9_budget_is_checked_after_the_occurrences(self):
        self.svc.book("bob", "r1", D(18, 10), D(18, 11), 2)
        with self.assertRaises(Conflict):
            self.series("yan", "r1", D(4), 4)

    # R10: series message

    def test_r10_one_message_per_series(self):
        self.series("ann", "r1", D(4), 3)
        self.assertEqual(self.messages(), [
            ("Series booked: Boardroom", "3 bookings of Boardroom, first Tue 04 Jun 10:00-11:00, total $180.00")])
        self.assertEqual(self.outbox.messages[0].user_id, "ann")

    def test_r10_message_total_uses_the_discount(self):
        self.series("ann", "r1", D(4), 4, hours=2)
        self.assertEqual(self.messages()[0][1], "4 bookings of Boardroom, first Tue 04 Jun 10:00-12:00, total $432.00")

    # R11, R12, R13, R14: cancellation fees

    def cancel_at(self, when, user="bob", room="r1", start=None, hours=1, series=False):
        b = self.book(user, room, start or D(4, 10), hours=hours)
        self.clock.set(when)
        return b, self.svc.cancel(user, b.id, series=series) if series else self.svc.cancel(user, b.id)

    def test_r11_exactly_24_hours_is_free(self):
        self.cancel_at(D(3, 10))
        self.assertEqual((self.team("ops").fees_cents, self.team("ops").budget_cents), (0, 1_000_000))

    def test_r11_just_inside_24_hours_costs_half(self):
        self.cancel_at(D(3, 10, 1))
        self.assertEqual((self.team("ops").fees_cents, self.team("ops").budget_cents), (3000, 1_000_000 - 3000))

    def test_r11_exactly_two_hours_is_still_half(self):
        self.cancel_at(D(4, 8))
        self.assertEqual(self.team("ops").fees_cents, 3000)

    def test_r11_inside_two_hours_costs_everything(self):
        self.cancel_at(D(4, 8, 1))
        self.assertEqual((self.team("ops").fees_cents, self.team("ops").budget_cents), (6000, 1_000_000 - 6000))

    def test_r11_half_fee_rounds_up(self):
        b = self.svc.book("bob", "r3", D(4, 10), D(4, 10, 30), 2)  # cost 501
        self.clock.set(D(4, 8))
        self.svc.cancel("bob", b.id)
        self.assertEqual(self.team("ops").fees_cents, 251)
        self.assertEqual(self.messages("bob")[-1][1], "Tue 04 Jun 10:00-10:30, refund $2.50, fee $2.51")

    def test_r12_team_totals_after_a_late_cancel(self):
        self.cancel_at(D(4, 8))
        t = self.team("ops")
        self.assertEqual((t.budget_cents, t.spent_cents, t.fees_cents), (997_000, 3000, 3000))

    def test_r12_fees_accumulate(self):
        self.cancel_at(D(4, 8, 30), start=D(4, 10))
        self.cancel_at(D(4, 10, 30), start=D(4, 11), user="cat")
        self.assertEqual(self.team("ops").fees_cents, 12000)

    def test_r13_started_booking_cannot_be_cancelled(self):
        b = self.book("bob", "r1", D(4, 10))
        for now in (D(4, 10), D(4, 10, 30), D(4, 12)):
            self.clock.set(now)
            with self.assertRaises(InvalidRequest) as ctx:
                self.svc.cancel("bob", b.id)
            self.assertEqual(str(ctx.exception), "booking has already started")
        self.assertEqual(b.status, "active")

    def test_r13_check_order(self):
        b = self.book("bob", "r1", D(4, 10))
        self.clock.set(D(4, 11))
        with self.assertRaises(NotAllowed):
            self.svc.cancel("cat", b.id)
        self.clock.set(D(3, 9))
        self.svc.cancel("bob", b.id)
        self.clock.set(D(4, 11))
        with self.assertRaises(InvalidRequest) as ctx:
            self.svc.cancel("bob", b.id)
        self.assertEqual(str(ctx.exception), "booking is already cancelled")

    def test_r14_message_bodies(self):
        self.cancel_at(D(3, 9))
        self.assertEqual(self.messages("bob")[-1], ("Cancelled: Boardroom", "Tue 04 Jun 10:00-11:00, refund $60.00"))
        self.cancel_at(D(4, 8), start=D(4, 13))
        self.assertEqual(self.messages("bob")[-1][1], "Tue 04 Jun 13:00-14:00, refund $30.00, fee $30.00")
        self.cancel_at(D(4, 12, 30), start=D(4, 14))
        self.assertEqual(self.messages("bob")[-1][1], "Tue 04 Jun 14:00-15:00, refund $0.00, fee $60.00")

    def test_r14_cancel_still_returns_the_booking(self):
        b, result = self.cancel_at(D(3, 9))
        self.assertIs(result, b)
        self.assertEqual(result.status, "cancelled")

    # R15, R16, R17: cancelling a series

    def ann_series(self, count=4, start=None):
        return self.series("ann", "r1", start or D(4), count)

    def test_r15_cancels_this_and_later_occurrences(self):
        made = self.ann_series()
        result = self.svc.cancel("ann", made[1].id, series=True)
        self.assertEqual([b.id for b in result], [made[1].id, made[2].id, made[3].id])
        self.assertEqual([b.status for b in made], ["active", "cancelled", "cancelled", "cancelled"])
        self.assertEqual(self.team("ops").budget_cents, 1_000_000 - 21600 + 16200)

    def test_r15_already_cancelled_occurrences_are_left_out(self):
        made = self.ann_series()
        self.svc.cancel("ann", made[2].id)
        result = self.svc.cancel("ann", made[1].id, series=True)
        self.assertEqual([b.id for b in result], [made[1].id, made[3].id])
        self.assertEqual(self.messages("ann")[-1][1], "2 bookings cancelled, refund $108.00, fee $0.00")

    def test_r15_each_occurrence_has_its_own_fee(self):
        made = self.ann_series()
        self.clock.set(D(4, 8))  # two hours before the first occurrence
        self.svc.cancel("ann", made[0].id, series=True)
        t = self.team("ops")
        self.assertEqual((t.fees_cents, t.budget_cents), (2700, 1_000_000 - 21600 + 2700 + 16200))
        self.assertEqual(self.messages("ann")[-1],
                         ("Series cancelled: Boardroom", "4 bookings cancelled, refund $189.00, fee $27.00"))

    def test_r15_fee_uses_the_discounted_cost(self):
        made = self.ann_series()
        self.clock.set(D(4, 9))
        self.svc.cancel("ann", made[0].id, series=True)
        self.assertEqual(self.team("ops").fees_cents, 5400)  # under two hours: all of 5400, not of 6000

    def test_r16_series_message_goes_to_the_owner(self):
        made = self.ann_series(count=3)
        self.svc.cancel("dan", made[0].id, series=True)
        self.assertEqual(self.messages("ann")[-1],
                         ("Series cancelled: Boardroom", "3 bookings cancelled, refund $180.00, fee $0.00"))
        self.assertEqual(len([m for m in self.outbox.messages if m.subject.startswith("Series cancelled")]), 1)
        self.assertEqual(self.messages("dan"), [])

    def test_r16_checks_apply_to_the_named_booking(self):
        made = self.ann_series()
        with self.assertRaises(NotAllowed):
            self.svc.cancel("bob", made[0].id, series=True)
        self.clock.set(D(4, 10, 30))
        with self.assertRaises(InvalidRequest) as ctx:
            self.svc.cancel("ann", made[0].id, series=True)
        self.assertEqual(str(ctx.exception), "booking has already started")
        self.svc.cancel("ann", made[1].id, series=True)  # later ones can still go
        self.assertEqual([b.status for b in made], ["active", "cancelled", "cancelled", "cancelled"])
        with self.assertRaises(InvalidRequest) as ctx:
            self.svc.cancel("ann", made[1].id, series=True)
        self.assertEqual(str(ctx.exception), "booking is already cancelled")

    def test_r17_series_false_cancels_one(self):
        made = self.ann_series()
        result = self.svc.cancel("ann", made[1].id)
        self.assertIsInstance(result, Booking)
        self.assertEqual([b.status for b in made], ["active", "cancelled", "active", "active"])
        self.assertEqual(self.messages("ann")[-1][0], "Cancelled: Boardroom")

    def test_r17_series_flag_on_a_single_booking(self):
        b = self.book("bob", "r1", D(5, 9))
        result = self.svc.cancel("bob", b.id, series=True)
        self.assertEqual(result, [b])
        self.assertEqual(self.messages("bob")[-1], ("Cancelled: Boardroom", "Wed 05 Jun 09:00-10:00, refund $60.00"))

    def test_r17_series_flag_on_the_last_occurrence_still_uses_the_series_message(self):
        made = self.ann_series(count=4)
        result = self.svc.cancel("ann", made[3].id, series=True)
        self.assertEqual(result, [made[3]])
        self.assertEqual(self.messages("ann")[-1],
                         ("Series cancelled: Boardroom", "1 bookings cancelled, refund $54.00, fee $0.00"))

    # R18: waitlist

    def blocked(self):
        return self.book("bob", "r1", D(4, 10))

    def test_r18_conflict_goes_to_the_waitlist(self):
        self.blocked()
        budget = self.team("ops").budget_cents
        entry = self.book("cat", "r1", D(4, 10), attendees=3, waitlist=True)
        self.assertIsInstance(entry, entry_cls())
        self.assertEqual((entry.id, entry.user_id, entry.room_id, entry.start, entry.end, entry.attendees,
                          entry.created), (1, "cat", "r1", D(4, 10), D(4, 11), 3, D(3, 8)))
        self.assertEqual(self.store.waitlist, {1: entry})
        self.assertEqual(self.team("ops").budget_cents, budget)
        self.assertEqual(self.messages("cat"), [("Waitlisted: Boardroom", "Tue 04 Jun 10:00-11:00 for 3 attendees")])

    def test_r18_entry_ids_are_their_own_counter(self):
        self.blocked()
        first = self.book("cat", "r1", D(4, 10), waitlist=True)
        second = self.book("ann", "r1", D(4, 10, 30), waitlist=True)
        self.assertEqual((first.id, second.id), (1, 2))
        self.assertEqual(self.book("cat", "r1", D(5, 10)).id, 2)

    def test_r18_other_problems_still_raise(self):
        self.blocked()
        with self.assertRaises(InvalidRequest):
            self.book("cat", "r1", D(4, 7), waitlist=True)
        with self.assertRaises(InvalidRequest) as ctx:
            self.book("cat", "r1", D(4, 10), attendees=11, waitlist=True)
        self.assertEqual(str(ctx.exception), "attendees must be between 1 and 10")
        with self.assertRaises(NotAllowed):
            self.book("gus", "r1", D(4, 10), waitlist=True)
        self.clock.set(D(4, 9, 50))
        with self.assertRaises(InvalidRequest):
            self.book("cat", "r1", D(4, 10), waitlist=True)
        self.assertEqual(self.store.waitlist, {})

    def test_r18_budget_is_not_checked_when_waitlisting(self):
        self.blocked()
        entry = self.book("fay", "r1", D(4, 10), hours=3, waitlist=True)
        self.assertEqual(entry.user_id, "fay")
        self.assertEqual(self.team("tiny").budget_cents, 6000)

    def test_r18_free_room_books_normally(self):
        result = self.book("cat", "r1", D(4, 10), waitlist=True)
        self.assertIsInstance(result, Booking)
        self.assertEqual(self.messages("cat")[0][0], "Booked: Boardroom")
        self.assertEqual(self.store.waitlist, {})

    # R19, R20: promotion

    def test_r19_cancelled_slot_goes_to_the_waiting_user(self):
        blocker = self.blocked()
        self.book("cat", "r1", D(4, 10), attendees=3, waitlist=True)
        self.svc.cancel("bob", blocker.id)
        new = self.store.bookings[2]
        self.assertEqual((new.user_id, new.team, new.room_id, new.start, new.end, new.attendees, new.cost_cents,
                          new.status, new.series_id, new.created), ("cat", "ops", "r1", D(4, 10), D(4, 11), 3, 6000,
                                                                    "active", None, D(3, 8)))
        self.assertEqual(self.store.waitlist, {})
        self.assertEqual(self.messages("cat")[-1],
                         ("Booked from waitlist: Boardroom", "Tue 04 Jun 10:00-11:00 for 3 attendees, $60.00"))
        self.assertEqual([m[0] for m in self.messages()],
                         ["Booked: Boardroom", "Waitlisted: Boardroom", "Cancelled: Boardroom",
                          "Booked from waitlist: Boardroom"])
        self.assertEqual(self.team("ops").budget_cents, 1_000_000 - 6000)

    def test_r19_first_come_first_served(self):
        blocker = self.blocked()
        self.book("cat", "r1", D(4, 10), waitlist=True)
        self.book("ann", "r1", D(4, 10), waitlist=True)
        self.svc.cancel("bob", blocker.id)
        self.assertEqual(self.store.bookings[2].user_id, "cat")
        self.assertEqual(list(self.store.waitlist), [2])

    def test_r19_later_entries_see_earlier_promotions(self):
        blocker = self.book("bob", "r1", D(4, 10), hours=1.5)
        self.book("cat", "r1", D(4, 10), waitlist=True)
        self.book("ann", "r1", D(4, 10, 30), waitlist=True)
        self.svc.cancel("bob", blocker.id)
        self.assertEqual([b.user_id for b in self.store.active_for_room("r1")], ["cat"])
        self.assertEqual(list(self.store.waitlist), [2])

    def test_r19_independent_entries_are_all_booked(self):
        blocker = self.book("bob", "r1", D(4, 10), hours=2)
        self.book("cat", "r1", D(4, 10), waitlist=True)
        self.book("ann", "r1", D(4, 11), waitlist=True)
        self.svc.cancel("bob", blocker.id)
        self.assertEqual([(b.user_id, b.start.hour) for b in self.store.active_for_room("r1")],
                         [("cat", 10), ("ann", 11)])
        self.assertEqual(self.store.waitlist, {})

    def test_r19_entries_of_other_rooms_wait(self):
        other = self.book("rex", "r2", D(4, 10))
        self.book("ann", "r2", D(4, 10), waitlist=True)
        mine = self.blocked()
        self.svc.cancel("bob", mine.id)
        self.assertEqual(list(self.store.waitlist), [1])
        self.svc.cancel("rex", other.id)
        self.assertEqual(self.store.waitlist, {})
        self.assertEqual(self.store.active_for_room("r2")[0].user_id, "ann")

    def test_r19_late_entry_is_dropped(self):
        blocker = self.blocked()
        self.book("cat", "r1", D(4, 10), waitlist=True)
        self.clock.set(D(4, 9, 50))
        self.svc.cancel("bob", blocker.id)
        self.assertEqual(self.store.waitlist, {})
        self.assertEqual(self.store.active_for_room("r1"), [])
        self.assertNotIn("Booked from waitlist: Boardroom", [m[0] for m in self.messages("cat")])

    def test_r19_entry_that_just_fits_the_lead_time_is_kept(self):
        blocker = self.blocked()
        self.book("cat", "r1", D(4, 10), waitlist=True)
        self.clock.set(D(4, 9, 45))
        self.svc.cancel("bob", blocker.id)
        self.assertEqual([b.user_id for b in self.store.active_for_room("r1")], ["cat"])

    def test_r19_refund_pays_for_the_waiting_booking(self):
        mine = self.book("fay", "r1", D(4, 10))
        self.assertEqual(self.team("tiny").budget_cents, 0)
        self.book("hal", "r1", D(4, 10), waitlist=True)
        self.svc.cancel("fay", mine.id)
        self.assertEqual([b.user_id for b in self.store.active_for_room("r1")], ["hal"])
        self.assertEqual(self.team("tiny").budget_cents, 0)

    def test_r19_entry_stays_when_the_team_cannot_pay(self):
        mine = self.book("fay", "r1", D(4, 10))
        self.book("hal", "r1", D(4, 10), waitlist=True)
        self.clock.set(D(4, 8, 30))  # under two hours: no refund
        self.svc.cancel("fay", mine.id)
        self.assertEqual(self.store.active_for_room("r1"), [])
        self.assertEqual(list(self.store.waitlist), [1])
        self.assertEqual(self.team("tiny").budget_cents, 0)
        self.assertEqual(self.messages("hal")[-1][0], "Waitlisted: Boardroom")

    def test_r19_every_cancellation_in_the_room_triggers_another_look(self):
        first = self.book("fay", "r1", D(4, 10))
        self.book("hal", "r1", D(4, 10), waitlist=True)
        self.clock.set(D(4, 8, 30))
        self.svc.cancel("fay", first.id)
        self.assertEqual(list(self.store.waitlist), [1])
        self.team("tiny").budget_cents += 6000  # the team can pay now
        other = self.book("ann", "r1", D(5, 10))
        self.svc.cancel("ann", other.id)
        self.assertEqual([b.user_id for b in self.store.active_for_room("r1")], ["hal"])
        self.assertEqual(self.store.waitlist, {})

    def test_r19_series_cancellation_promotes_afterwards(self):
        made = self.ann_series()
        self.book("cat", "r1", D(18, 10), waitlist=True)
        self.svc.cancel("ann", made[0].id, series=True)
        self.assertEqual([m[0] for m in self.messages()][-2:], ["Series cancelled: Boardroom",
                                                                "Booked from waitlist: Boardroom"])
        booked = self.store.active_for_room("r1")
        self.assertEqual([(b.user_id, b.start, b.cost_cents) for b in booked], [("cat", D(18, 10), 6000)])
        self.assertEqual(self.store.waitlist, {})

    def test_r19_nothing_is_promoted_without_a_cancellation(self):
        self.blocked()
        self.book("cat", "r1", D(4, 10), waitlist=True)
        self.book("ann", "r1", D(5, 10))
        self.assertEqual(list(self.store.waitlist), [1])

    def test_r20_promoted_booking_is_an_ordinary_one(self):
        blocker = self.blocked()
        self.book("cat", "r1", D(4, 10), waitlist=True)
        self.clock.set(D(3, 9))
        self.svc.cancel("bob", blocker.id)
        booking = self.store.active_for_room("r1")[0]
        self.assertIsNone(booking.series_id)
        self.assertEqual(booking.created, D(3, 9))
        self.assertEqual(self.series("ann", "r1", D(5), 2)[0].series_id, 1)

    # R21: leaving the waitlist

    def test_r21_leave(self):
        self.blocked()
        entry = self.book("cat", "r1", D(4, 10), waitlist=True)
        sent = len(self.outbox.messages)
        self.svc.leave_waitlist("cat", entry.id)
        self.assertEqual(self.store.waitlist, {})
        self.assertEqual(len(self.outbox.messages), sent)

    def test_r21_only_the_owner_may_leave(self):
        self.blocked()
        entry = self.book("cat", "r1", D(4, 10), waitlist=True)
        for who in ("ann", "dan", "bob"):
            with self.assertRaises(NotAllowed) as ctx:
                self.svc.leave_waitlist(who, entry.id)
            self.assertEqual(str(ctx.exception), "you cannot leave this waitlist entry")
        self.assertEqual(list(self.store.waitlist), [1])

    def test_r21_unknown_entry(self):
        with self.assertRaises(NotFound) as ctx:
            self.svc.leave_waitlist("cat", 7)
        self.assertEqual(str(ctx.exception), "unknown waitlist entry 7")

    def test_r21_a_left_entry_is_not_promoted(self):
        blocker = self.blocked()
        entry = self.book("cat", "r1", D(4, 10), waitlist=True)
        self.svc.leave_waitlist("cat", entry.id)
        self.svc.cancel("bob", blocker.id)
        self.assertEqual(self.store.active_for_room("r1"), [])

    # R22: money format

    def test_r22_thousands_separators(self):
        self.assertEqual(money(5), "$0.05")
        self.assertEqual(money(99999), "$999.99")
        self.assertEqual(money(123456), "$1,234.56")
        self.assertEqual(money(100_000_000), "$1,000,000.00")

    def test_r22_messages_and_errors_use_them(self):
        self.book("rex", "r5", D(4, 10))
        self.assertEqual(self.messages("rex")[0][1], "Tue 04 Jun 10:00-11:00 for 2 attendees, $1,234.56")
        with self.assertRaises(InsufficientBudget) as ctx:
            self.book("fay", "r5", D(5, 10))
        self.assertEqual(str(ctx.exception), "team budget too low: need $1,234.56, have $60.00")

    def test_r22_slot_is_unchanged(self):
        self.assertEqual(slot(D(9, 9), D(9, 10, 15)), "Sun 09 Jun 09:00-10:15")

    # R23: spend report

    def test_r23_fees_in_the_spend_report(self):
        self.cancel_at(D(4, 8))
        lines = spend_report(self.store).splitlines()
        self.assertIn("ops: $30.00 spent, $9,970.00 left, $30.00 in fees", lines)
        self.assertIn("tiny: $0.00 spent, $60.00 left", lines)
        self.assertEqual(lines, sorted(lines))

    def test_r23_no_suffix_without_fees(self):
        b = self.book("bob", "r1", D(5, 9))
        self.svc.cancel("bob", b.id)
        self.assertIn("ops: $0.00 spent, $10,000.00 left", spend_report(self.store).splitlines())

    # R24: waitlist report

    def test_r24_empty(self):
        self.assertEqual(waitlist_report(self.store), "Waitlist is empty")

    def test_r24_counts_and_order(self):
        self.store.add_room(Room("r6", "apple", 5, 1000))
        self.store.add_room(Room("r7", "Banana", 5, 1000))
        for i, room in enumerate(("r7", "r6", "r1", "r7"), start=1):
            self.store.waitlist[i] = entry_cls()(i, "cat", room, D(4, 10), D(4, 11), 2, D(3, 8))
        self.assertEqual(waitlist_report(self.store).splitlines(),
                         ["apple: 1 waiting", "Banana: 2 waiting", "Boardroom: 1 waiting"])

    def test_r24_follows_the_real_waitlist(self):
        blocker = self.blocked()
        self.book("cat", "r1", D(4, 10), waitlist=True)
        self.assertEqual(waitlist_report(self.store), "Boardroom: 1 waiting")
        self.svc.cancel("bob", blocker.id)
        self.assertEqual(waitlist_report(self.store), "Waitlist is empty")

    # R25: rules that meet

    def test_r25_series_cancel_refund_can_pay_a_waiting_team_mate(self):
        s = self.store
        s.add_team("duo", 21600)
        s.add_user(User("mia", "Mia", "manager", "duo"))
        s.add_user(User("sam", "Sam", "staff", "duo"))
        made = self.series("mia", "r1", D(4), 4)
        self.assertEqual(self.team("duo").budget_cents, 0)
        self.book("sam", "r1", D(11), waitlist=True)
        self.svc.cancel("mia", made[0].id, series=True)
        self.assertEqual([(b.user_id, b.start) for b in s.active_for_room("r1")], [("sam", D(11))])
        self.assertEqual(self.team("duo").budget_cents, 21600 - 6000)

    def test_r25_conflicts_use_active_bookings_only(self):
        made = self.ann_series(count=2)
        self.svc.cancel("ann", made[1].id)
        again = self.book("bob", "r1", D(11, 10))
        self.assertEqual(again.status, "active")


if __name__ == "__main__":
    unittest.main()
