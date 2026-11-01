"""Hidden tests for t46-library-reservations. Every rule is shown by the starting code; see AUDIT.md."""
import unittest

from lendr import Service
from lendr.clock import FixedClock
from lendr.errors import Conflict, LendrError, NotFound

T0 = "2026-01-05T09:00:00Z"


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.dune = self.svc.call("book.create", title="Dune", copies=1)["id"]
        self.emma = self.svc.call("book.create", title="Emma", copies=2)["id"]
        self.ada = self.svc.call("member.create", name="Ada")["id"]
        self.bob = self.svc.call("member.create", name="Bob")["id"]
        self.cy = self.svc.call("member.create", name="Cy")["id"]
        self.loan = self.svc.call("loan.checkout", book=self.dune, member=self.ada)["id"]
        self.svc.bus.log.clear()

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def reserve(self, member=None, book=None):
        return self.call("reservation.create", book=book or self.dune, member=member or self.bob)

    def book(self, book_id=None):
        return self.call("book.retrieve", book=book_id or self.dune)

    def res(self, res_id):
        return self.call("reservation.retrieve", reservation=res_id)

    def types(self):
        return [e["type"] for e in self.svc.bus.log]

    def assertError(self, cls, param, op, **params):
        with self.assertRaises(cls) as ctx:
            self.call(op, **params)
        self.assertIsInstance(ctx.exception, LendrError)
        self.assertEqual(ctx.exception.param, param)


class TestPlace(Base):
    def test_operations_are_registered(self):
        ops = set(self.svc.operations())
        self.assertTrue({"reservation.create", "reservation.cancel", "reservation.retrieve"} <= ops)
        self.assertTrue({"loan.checkout", "book.retire"} <= ops)

    def test_reservation_view(self):
        r = self.reserve()
        self.assertEqual(r["id"], "reservation_0001")
        self.assertEqual((r["book"], r["member"], r["status"], r["pickup_by"]), (self.dune, self.bob, "waiting", None))
        self.assertEqual((r["created_at"], r["updated_at"], r["version"]), (T0, T0, 1))

    def test_ids_are_sequential(self):
        self.assertEqual([self.reserve(self.bob)["id"], self.reserve(self.cy)["id"]], ["reservation_0001", "reservation_0002"])

    def test_create_event_carries_the_returned_view(self):
        r = self.reserve()
        self.assertEqual(self.svc.bus.log, [{"type": "reservation.created", "data": {"reservation": r}}])

    def test_ids_are_given_to_extra_records_only_after_validation(self):
        for params in ({"book": "book_9999", "member": self.bob}, {"book": self.dune, "member": "mem_9999"}):
            with self.assertRaises(NotFound):
                self.call("reservation.create", **params)
        self.assertEqual(self.reserve()["id"], "reservation_0001")

    def test_book_is_checked_before_member(self):
        self.assertError(NotFound, "book", "reservation.create", book="book_9999", member="mem_9999")
        self.assertError(NotFound, "member", "reservation.create", book=self.dune, member="mem_9999")

    def test_ids_are_read_like_other_strings(self):
        self.assertEqual(self.reserve(member="  " + self.bob + " ")["member"], self.bob)
        self.assertError(LendrError, "book", "reservation.create", member=self.bob)

    def test_a_book_with_a_free_copy_cannot_be_reserved(self):
        with self.assertRaises(Conflict):
            self.call("reservation.create", book=self.emma, member=self.bob)

    def test_a_suspended_member_cannot_reserve(self):
        self.call("member.suspend", member=self.bob)
        self.assertError(Conflict, "member", "reservation.create", book=self.dune, member=self.bob)

    def test_a_retired_book_cannot_be_reserved(self):
        self.call("book.retire", book=self.dune)
        with self.assertRaises(Conflict):
            self.call("reservation.create", book=self.dune, member=self.bob)

    def test_failures_change_nothing(self):
        with self.assertRaises(Conflict):
            self.call("reservation.create", book=self.emma, member=self.bob)
        self.assertEqual(self.types(), [])
        self.assertEqual(self.reserve()["id"], "reservation_0001")

    def test_a_member_cannot_wait_twice_or_reserve_what_they_hold(self):
        self.reserve()
        for member in (self.bob, self.ada):
            with self.assertRaises(Conflict):
                self.call("reservation.create", book=self.dune, member=member)

    def test_unknown_reservation(self):
        self.assertError(NotFound, "reservation", "reservation.retrieve", reservation="reservation_0009")
        self.assertError(NotFound, "reservation", "reservation.cancel", reservation="reservation_0009")
        self.assertError(LendrError, "reservation", "reservation.retrieve")


class TestReady(Base):
    def test_return_makes_the_first_in_line_ready(self):
        first, second = self.reserve(self.bob), self.reserve(self.cy)
        self.clock.advance(hours=2)
        self.call("loan.return", loan=self.loan)
        r = self.res(first["id"])
        self.assertEqual((r["status"], r["pickup_by"], r["version"]), ("ready", "2026-01-08T11:00:00Z", 2))
        self.assertEqual(r["updated_at"], "2026-01-05T11:00:00Z")
        self.assertEqual(self.res(second["id"])["status"], "waiting")
        self.assertEqual(self.res(second["id"])["version"], 1)

    def test_events_of_a_return_come_in_order(self):
        r = self.reserve()
        self.call("loan.return", loan=self.loan)
        self.assertEqual(self.types(), ["reservation.created", "loan.returned", "reservation.ready"])
        last = self.svc.bus.log[-1]["data"]["reservation"]
        self.assertEqual((last["id"], last["status"]), (r["id"], "ready"))
        self.assertEqual(last, self.res(r["id"]))

    def test_return_without_a_queue_does_not_emit_ready(self):
        self.call("loan.return", loan=self.loan)
        self.assertEqual(self.types(), ["loan.returned"])

    def test_return_value_is_unchanged(self):
        self.reserve()
        out = self.call("loan.return", loan=self.loan)
        self.assertEqual((out["id"], out["status"], out["version"]), (self.loan, "returned", 2))

    def test_a_held_copy_is_not_available(self):
        self.reserve()
        self.call("loan.return", loan=self.loan)
        self.assertEqual(self.book()["available"], 0)
        self.assertError(Conflict, "book", "loan.checkout", book=self.dune, member=self.cy)

    def test_the_other_book_is_not_touched(self):
        self.call("loan.checkout", book=self.emma, member=self.ada)
        self.call("loan.checkout", book=self.emma, member=self.bob)
        self.reserve(self.cy, self.emma)
        self.reserve(self.bob)
        self.call("loan.return", loan=self.loan)
        self.assertEqual(self.res("reservation_0001")["status"], "waiting")
        self.assertEqual(self.res("reservation_0002")["status"], "ready")
        self.assertEqual(self.book(self.emma)["available"], 0)

    def test_a_free_copy_stays_free_when_nobody_waits(self):
        self.call("loan.return", loan=self.loan)
        self.assertEqual(self.book()["available"], 1)
        self.call("loan.checkout", book=self.dune, member=self.cy)

    def test_two_copies_two_ready(self):
        a = self.call("loan.checkout", book=self.emma, member=self.ada)["id"]
        b = self.call("loan.checkout", book=self.emma, member=self.bob)["id"]
        self.reserve(self.cy, self.emma)
        self.call("loan.return", loan=a)
        self.assertEqual(self.book(self.emma)["available"], 0)
        self.call("loan.return", loan=b)
        self.assertEqual(self.book(self.emma)["available"], 1)

    def test_late_return_still_hands_over_and_charges_the_fine(self):
        r = self.reserve()
        self.clock.advance(days=20)
        self.call("loan.return", loan=self.loan)
        self.assertEqual(self.svc.bus.log[1]["type"], "loan.returned")
        self.assertEqual(sorted(self.types()[2:]), ["fine.charged", "reservation.ready"])
        self.assertEqual(self.res(r["id"])["pickup_by"], "2026-01-28T09:00:00Z")


class TestFulfil(Base):
    def make_ready(self):
        r = self.reserve()
        self.call("loan.return", loan=self.loan)
        self.svc.bus.log.clear()
        return r

    def test_checkout_by_the_holder_fulfils(self):
        r = self.make_ready()
        self.clock.advance(days=1)
        loan = self.call("loan.checkout", book=self.dune, member=self.bob)
        self.assertEqual((loan["id"], loan["status"]), ("loan_0002", "open"))
        done = self.res(r["id"])
        self.assertEqual((done["status"], done["version"], done["updated_at"]), ("fulfilled", 3, "2026-01-06T09:00:00Z"))
        self.assertEqual(self.book()["available"], 0)

    def test_checkout_events_come_in_order(self):
        r = self.make_ready()
        loan = self.call("loan.checkout", book=self.dune, member=self.bob)
        self.assertEqual(self.types(), ["loan.created", "reservation.fulfilled"])
        self.assertEqual(self.svc.bus.log[0]["data"], {"loan": loan})
        self.assertEqual(self.svc.bus.log[1]["data"], {"reservation": self.res(r["id"])})

    def test_checkout_by_someone_else_changes_nothing(self):
        self.make_ready()
        self.assertError(Conflict, "book", "loan.checkout", book=self.dune, member=self.cy)
        self.assertEqual(self.types(), [])
        self.assertEqual(self.call("loan.checkout", book=self.dune, member=self.bob)["id"], "loan_0002")

    def test_a_fulfilled_reservation_cannot_be_cancelled(self):
        r = self.make_ready()
        self.call("loan.checkout", book=self.dune, member=self.bob)
        self.assertError(Conflict, "reservation", "reservation.cancel", reservation=r["id"])

    def test_checkout_without_a_reservation_emits_one_event(self):
        self.call("loan.return", loan=self.loan)
        self.svc.bus.log.clear()
        self.call("loan.checkout", book=self.dune, member=self.cy)
        self.assertEqual(self.types(), ["loan.created"])


class TestCancel(Base):
    def test_cancel_a_waiting_reservation(self):
        r = self.reserve()
        self.clock.advance(minutes=5)
        out = self.call("reservation.cancel", reservation=r["id"])
        self.assertEqual((out["status"], out["version"], out["updated_at"]), ("cancelled", 2, "2026-01-05T09:05:00Z"))
        self.assertEqual(self.types(), ["reservation.created", "reservation.cancelled"])
        self.assertEqual(self.svc.bus.log[-1]["data"], {"reservation": out})

    def test_a_cancelled_reservation_is_skipped_on_return(self):
        a, b = self.reserve(self.bob), self.reserve(self.cy)
        self.call("reservation.cancel", reservation=a["id"])
        self.call("loan.return", loan=self.loan)
        self.assertEqual(self.res(a["id"])["status"], "cancelled")
        self.assertEqual(self.res(b["id"])["status"], "ready")

    def test_cancelling_a_ready_reservation_passes_the_copy_on(self):
        a, b = self.reserve(self.bob), self.reserve(self.cy)
        self.call("loan.return", loan=self.loan)
        self.svc.bus.log.clear()
        self.clock.advance(days=1)
        out = self.call("reservation.cancel", reservation=a["id"])
        self.assertEqual(out["status"], "cancelled")
        self.assertEqual(self.types(), ["reservation.cancelled", "reservation.ready"])
        second = self.res(b["id"])
        self.assertEqual((second["status"], second["pickup_by"]), ("ready", "2026-01-09T09:00:00Z"))
        self.assertEqual(self.svc.bus.log[1]["data"], {"reservation": second})
        self.assertEqual(self.book()["available"], 0)

    def test_cancelling_the_last_ready_reservation_frees_the_copy(self):
        a = self.reserve()
        self.call("loan.return", loan=self.loan)
        self.svc.bus.log.clear()
        self.call("reservation.cancel", reservation=a["id"])
        self.assertEqual(self.types(), ["reservation.cancelled"])
        self.assertEqual(self.book()["available"], 1)
        self.call("loan.checkout", book=self.dune, member=self.cy)

    def test_cancel_conflicts_change_nothing(self):
        r = self.reserve()
        self.call("reservation.cancel", reservation=r["id"])
        self.svc.bus.log.clear()
        self.assertError(Conflict, "reservation", "reservation.cancel", reservation=r["id"])
        self.assertEqual(self.types(), [])
        self.assertEqual(self.res(r["id"])["version"], 2)

    def test_retrieve_emits_nothing(self):
        r = self.reserve()
        self.svc.bus.log.clear()
        self.res(r["id"])
        self.assertEqual(self.types(), [])


class TestExisting(Base):
    def test_retire_still_orders_its_events(self):
        self.call("book.retire", book=self.dune)
        self.assertEqual(self.types(), ["book.retired", "loan.returned"])

    def test_late_fine_order_is_unchanged(self):
        self.clock.advance(days=15)
        self.call("loan.return", loan=self.loan)
        self.assertEqual(self.types(), ["loan.returned", "fine.charged"])
        self.assertEqual(self.call("loan.fines", member=self.ada)["data"][0]["amount"], 25)


if __name__ == "__main__":
    unittest.main()
