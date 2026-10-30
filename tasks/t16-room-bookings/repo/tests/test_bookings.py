import unittest
from datetime import date, datetime

from bookings import (BookingService, Clock, Conflict, InvalidRequest, NotAllowed, Outbox, Room, Store, User)
from bookings.report import utilization


def make():
    store = Store()
    store.add_room(Room("r1", "Boardroom", 10, 6000))
    store.add_room(Room("r2", "Atrium", 6, 4000, "premium"))
    store.add_team("ops", 100_000)
    store.add_user(User("ann", "Ann", "manager", "ops"))
    store.add_user(User("bob", "Bob", "staff", "ops"))
    store.add_user(User("gus", "Gus", "guest", "ops"))
    clock = Clock(datetime(2024, 6, 3, 8, 0))
    outbox = Outbox()
    return BookingService(store, clock, outbox), store, outbox


class TestBookings(unittest.TestCase):
    def test_book_and_charge(self):
        svc, store, outbox = make()
        b = svc.book("bob", "r1", datetime(2024, 6, 4, 9, 0), datetime(2024, 6, 4, 10, 30), 4)
        self.assertEqual(b.cost_cents, 9000)
        self.assertEqual(store.team("ops").budget_cents, 91_000)
        self.assertEqual(outbox.messages[0].subject, "Booked: Boardroom")

    def test_conflict_and_permissions(self):
        svc, _, _ = make()
        svc.book("bob", "r1", datetime(2024, 6, 4, 9, 0), datetime(2024, 6, 4, 10, 0), 2)
        with self.assertRaises(Conflict):
            svc.book("ann", "r1", datetime(2024, 6, 4, 9, 30), datetime(2024, 6, 4, 10, 30), 2)
        with self.assertRaises(NotAllowed):
            svc.book("gus", "r1", datetime(2024, 6, 4, 12, 0), datetime(2024, 6, 4, 13, 0), 2)
        with self.assertRaises(InvalidRequest):
            svc.book("ann", "r1", datetime(2024, 6, 4, 12, 0), datetime(2024, 6, 4, 12, 15), 2)

    def test_cancel_refunds_everything(self):
        svc, store, _ = make()
        b = svc.book("bob", "r1", datetime(2024, 6, 4, 9, 0), datetime(2024, 6, 4, 10, 0), 2)
        svc.cancel("bob", b.id)
        self.assertEqual(store.team("ops").budget_cents, 100_000)

    def test_utilization(self):
        svc, _, _ = make()
        svc.book("bob", "r1", datetime(2024, 6, 4, 9, 0), datetime(2024, 6, 4, 10, 30), 2)
        self.assertEqual(utilization(svc.store, date(2024, 6, 3), date(2024, 6, 7)).splitlines()[1],
                         "Boardroom" + " " * 10 + "3.0%  1.5h")

    def test_free_slots_and_agenda(self):
        from bookings.report import agenda
        from bookings.slots import free_starts, next_free_start
        svc, store, _ = make()
        day = date(2024, 6, 4)
        svc.book("bob", "r1", datetime(2024, 6, 4, 9, 0), datetime(2024, 6, 4, 10, 0), 2)
        starts = free_starts(store, "r1", day, 60)
        self.assertNotIn(datetime(2024, 6, 4, 9, 30), starts)
        self.assertIn(datetime(2024, 6, 4, 10, 0), starts)
        self.assertEqual(next_free_start(store, "r1", day, 60), datetime(2024, 6, 4, 8, 0))
        self.assertEqual(free_starts(store, "r1", date(2024, 6, 8), 60), [])
        self.assertEqual(agenda(store, day), "09:00-10:00 Boardroom (Bob, 2 people)")
        self.assertEqual(agenda(store, date(2024, 6, 5)), "Nothing booked")

    def test_messages_and_budget(self):
        from bookings import InsufficientBudget
        from bookings.fmt import money, slot
        self.assertEqual(money(1250), "$12.50")
        self.assertEqual(slot(datetime(2024, 6, 3, 9, 0), datetime(2024, 6, 3, 10, 30)), "Mon 03 Jun 09:00-10:30")
        svc, store, outbox = make()
        store.add_team("tiny", 1000)
        store.add_user(User("tim", "Tim", "staff", "tiny"))
        with self.assertRaises(InsufficientBudget) as ctx:
            svc.book("tim", "r1", datetime(2024, 6, 4, 9, 0), datetime(2024, 6, 4, 10, 0), 2)
        self.assertEqual(str(ctx.exception), "team budget too low: need $60.00, have $10.00")
        self.assertEqual(outbox.messages, [])

    def test_bookings_for_room(self):
        svc, _, _ = make()
        svc.book("bob", "r1", datetime(2024, 6, 4, 11, 0), datetime(2024, 6, 4, 12, 0), 2)
        svc.book("ann", "r1", datetime(2024, 6, 4, 9, 0), datetime(2024, 6, 4, 10, 0), 2)
        svc.book("ann", "r1", datetime(2024, 6, 5, 9, 0), datetime(2024, 6, 5, 10, 0), 2)
        found = svc.bookings_for_room("r1", date(2024, 6, 4))
        self.assertEqual([b.start.hour for b in found], [9, 11])


if __name__ == "__main__":
    unittest.main()
