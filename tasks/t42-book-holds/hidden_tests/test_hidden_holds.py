"""Hidden tests for t42-book-holds. Rules come from the prompt, the repo, or answers.json; see AUDIT.md."""
import unittest

from lending import Service
from lending.clock import FixedClock
from lending.errors import Conflict, InvalidRequest, LendingError, NotFound

T0 = "2026-01-05T09:00:00Z"


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.ann, self.bo, self.cy, self.di = [self.svc.call("member.create", name=n)["id"]
                                               for n in ("Ann", "Bo", "Cy", "Di")]
        self.books = [self.svc.call("book.create", title=t)["id"] for t in ("Dune", "Emma", "Ulysses", "Kim", "Ivanhoe")]
        self.dune = self.books[0]
        self.ann_loan = self.borrow(self.dune, self.ann)["id"]       # loan_0001
        self.svc.bus.log.clear()

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def borrow(self, book, member):
        return self.call("loan.borrow", book=book, member=member)

    def give_back(self, loan=None):
        return self.call("loan.return", loan=loan or self.ann_loan)

    def hold(self, member, book=None):
        return self.call("hold.place", book=book or self.dune, member=member)

    def status(self, hold_id):
        return self.call("hold.retrieve", hold=hold_id)["status"]

    def types(self):
        return [e["type"] for e in self.svc.bus.log]

    def assertError(self, cls, param, op, **params):
        with self.assertRaises(cls) as ctx:
            self.call(op, **params)
        self.assertIsInstance(ctx.exception, LendingError)
        self.assertEqual(ctx.exception.param, param)
        return ctx.exception

    def line_of_three(self):
        """Bo, Cy and Di wait for Dune, in that order; Ann still has it."""
        ids = [self.hold(m)["id"] for m in (self.bo, self.cy, self.di)]
        self.svc.bus.log.clear()
        return ids


class TestPlace(Base):
    def test_operations_are_registered(self):
        ops = set(self.svc.operations())
        self.assertTrue({"hold.place", "hold.cancel", "hold.collect", "hold.retrieve"} <= ops)
        self.assertTrue({"loan.borrow", "loan.return", "book.create"} <= ops)

    def test_hold_view(self):
        h = self.hold(self.bo)
        self.assertEqual(h["id"], "hold_0001")
        self.assertEqual((h["book"], h["member"], h["status"]), (self.dune, self.bo, "waiting"))
        self.assertEqual((h["created_at"], h["updated_at"], h["version"]), (T0, T0, 1))
        self.assertEqual(self.hold(self.cy)["id"], "hold_0002")

    def test_place_event(self):
        h = self.hold(self.bo)
        self.assertEqual(self.svc.bus.log, [{"type": "hold.placed", "data": {"hold": h}}])

    def test_unknown_book_and_member(self):
        self.assertError(NotFound, "book", "hold.place", book="book_9999", member=self.bo)
        self.assertError(NotFound, "member", "hold.place", book=self.dune, member="member_9999")

    def test_failures_change_nothing(self):
        with self.assertRaises(LendingError):
            self.call("hold.place", book="book_9999", member=self.bo)
        self.assertEqual(self.svc.bus.log, [])
        self.assertEqual(self.hold(self.bo)["id"], "hold_0001")

    def test_retrieve(self):
        h = self.hold(self.bo)
        self.svc.bus.log.clear()
        self.assertEqual(self.call("hold.retrieve", hold=h["id"]), h)
        self.assertEqual(self.svc.bus.log, [])
        self.assertError(NotFound, "hold", "hold.retrieve", hold="hold_9999")
        self.assertError(InvalidRequest, "hold", "hold.retrieve")


class TestQueue(Base):
    def test_return_offers_the_book_to_the_first_in_line(self):
        a, b, c = self.line_of_three()
        self.give_back()
        self.assertEqual([self.status(x) for x in (a, b, c)], ["ready", "waiting", "waiting"])

    def test_line_follows_the_order_placed_not_member_order(self):
        first = self.hold(self.di)["id"]
        self.clock.advance(hours=1)
        second = self.hold(self.bo)["id"]
        self.give_back()
        self.assertEqual((self.status(first), self.status(second)), ("ready", "waiting"))

    def test_ready_book_cannot_be_borrowed_by_others(self):
        self.hold(self.bo)
        self.give_back()
        self.assertError(Conflict, "book", "loan.borrow", book=self.dune, member=self.di)
        self.assertEqual(self.svc.bus.log[-1]["type"], "loan.returned")

    def test_collect_borrows_the_book(self):
        h = self.hold(self.bo)
        self.give_back()
        self.clock.advance(hours=5)
        self.svc.bus.log.clear()
        out = self.call("hold.collect", hold=h["id"])
        self.assertEqual((out["status"], out["version"], out["updated_at"]), ("collected", 3, "2026-01-05T14:00:00Z"))
        loan = self.call("loan.retrieve", loan="loan_0002")
        self.assertEqual((loan["book"], loan["member"], loan["status"], loan["due"]),
                         (self.dune, self.bo, "open", "2026-01-19T14:00:00Z"))
        self.assertEqual(self.svc.bus.log, [{"type": "hold.collected", "data": {"hold": out}}])
        self.assertError(Conflict, "book", "loan.borrow", book=self.dune, member=self.di)

    def test_collect_only_when_ready(self):
        h = self.hold(self.bo)
        self.assertError(Conflict, "hold", "hold.collect", hold=h["id"])
        self.assertEqual(self.svc.bus.log, [{"type": "hold.placed", "data": {"hold": h}}])

    def test_cancel_a_waiting_hold(self):
        a, b, c = self.line_of_three()
        out = self.call("hold.cancel", hold=a)
        self.assertEqual((out["status"], out["version"]), ("cancelled", 2))
        self.assertEqual(self.svc.bus.log, [{"type": "hold.cancelled", "data": {"hold": out}}])
        self.give_back()
        self.assertEqual((self.status(b), self.status(c)), ("ready", "waiting"))

    def test_cancelling_a_ready_hold_offers_the_next_in_line(self):
        a, b, c = self.line_of_three()
        self.give_back()
        self.call("hold.cancel", hold=a)
        self.assertEqual((self.status(a), self.status(b), self.status(c)), ("cancelled", "ready", "waiting"))

    def test_cancelling_the_last_ready_hold_frees_the_book(self):
        h = self.hold(self.bo)
        self.give_back()
        self.call("hold.cancel", hold=h["id"])
        self.assertEqual(self.borrow(self.dune, self.di)["member"], self.di)

    def test_return_emits_only_the_loan_event(self):
        self.line_of_three()
        out = self.give_back()
        self.assertEqual(self.svc.bus.log, [{"type": "loan.returned", "data": {"loan": out}}])

    def test_a_hold_that_is_done_cannot_be_resolved_again(self):
        h = self.hold(self.bo)["id"]
        self.give_back()
        self.call("hold.collect", hold=h)
        for op in ("hold.collect", "hold.cancel"):
            with self.subTest(op=op):
                self.assertError(Conflict, "hold", op, hold=h)
        g = self.hold(self.cy)["id"]
        self.call("hold.cancel", hold=g)
        for op in ("hold.collect", "hold.cancel"):
            with self.subTest(op=op, after="cancel"):
                self.assertError(Conflict, "hold", op, hold=g)

    def test_unknown_hold(self):
        for op in ("hold.collect", "hold.cancel"):
            with self.subTest(op=op):
                self.assertError(NotFound, "hold", op, hold="hold_9999")
                self.assertError(InvalidRequest, "hold", op)

    def test_other_books_are_independent(self):
        emma = self.books[1]
        loan = self.borrow(emma, self.cy)["id"]
        h_emma = self.hold(self.bo, emma)["id"]
        h_dune = self.hold(self.bo)["id"]
        self.give_back(loan)
        self.assertEqual((self.status(h_emma), self.status(h_dune)), ("ready", "waiting"))


class TestPickup(Base):
    """answers.json: pickup"""

    def ready_hold(self):
        h = self.hold(self.bo)["id"]
        self.give_back()                         # ready at T0, so it lapses at 2026-01-08T09:00:00Z
        return h

    def test_expires_at_in_the_view(self):
        h = self.hold(self.bo)
        self.assertIsNone(h["expires_at"])
        self.clock.advance(days=1)
        self.give_back()
        out = self.call("hold.retrieve", hold=h["id"])
        self.assertEqual(out["status"], "ready")
        self.assertEqual(out["expires_at"], "2026-01-09T09:00:00Z")
        self.assertIsNone(self.hold(self.cy)["expires_at"])

    def test_still_ready_a_second_before_the_end(self):
        h = self.ready_hold()
        self.clock.advance(hours=71, minutes=59, seconds=59)
        self.assertEqual(self.status(h), "ready")
        self.assertEqual(self.call("hold.collect", hold=h)["status"], "collected")

    def test_expired_at_the_moment_itself(self):
        h = self.ready_hold()
        self.clock.advance(hours=72)
        self.assertEqual(self.status(h), "expired")
        self.assertError(Conflict, "hold", "hold.collect", hold=h)

    def test_expired_cannot_be_cancelled(self):
        h = self.ready_hold()
        self.clock.advance(hours=80)
        self.assertError(Conflict, "hold", "hold.cancel", hold=h)

    def test_the_next_in_line_is_offered_when_it_lapses(self):
        a, b, c = self.line_of_three()
        self.give_back()                                  # Bo ready until 01-08T09:00
        self.clock.advance(hours=82)                      # Cy noticed 10 hours after Bo's lapse
        out = self.call("hold.retrieve", hold=b)
        self.assertEqual((self.status(a), out["status"]), ("expired", "ready"))
        self.assertEqual(out["expires_at"], "2026-01-11T09:00:00Z")      # 72h from the lapse, not from now
        self.assertEqual(self.status(c), "waiting")

    def test_the_whole_line_can_lapse_while_nobody_looks(self):
        a, b, c = self.line_of_three()
        self.give_back()
        self.clock.advance(days=6, hours=1)               # Bo lapsed at +3d, Cy at +6d; Di is ready until +9d
        self.assertEqual([self.status(x) for x in (a, b, c)], ["expired", "expired", "ready"])
        self.assertEqual(self.call("hold.retrieve", hold=c)["expires_at"], "2026-01-14T09:00:00Z")
        self.assertError(Conflict, "book", "loan.borrow", book=self.dune, member=self.ann)

    def test_after_the_last_lapse_the_book_is_free(self):
        a, b, c = self.line_of_three()
        self.give_back()
        self.clock.advance(days=9)
        self.assertEqual([self.status(x) for x in (a, b, c)], ["expired"] * 3)
        self.assertEqual(self.borrow(self.dune, self.ann)["member"], self.ann)

    def test_lapse_is_seen_by_borrow(self):
        self.ready_hold()
        self.clock.advance(hours=72)
        self.assertEqual(self.borrow(self.dune, self.di)["member"], self.di)

    def test_done_holds_never_expire(self):
        a = self.hold(self.bo)["id"]
        b = self.hold(self.cy)["id"]
        self.give_back()
        self.call("hold.collect", hold=a)
        self.call("hold.cancel", hold=b)
        self.clock.advance(days=10)
        self.assertEqual((self.status(a), self.status(b)), ("collected", "cancelled"))


class TestLimit(Base):
    """answers.json: limit"""

    def setUp(self):
        super().setUp()
        self.loans = {}
        for book in self.books[1:]:
            self.loans[book] = self.borrow(book, self.ann)["id"]
        self.svc.bus.log.clear()

    def test_three_holds_are_fine_and_the_fourth_is_refused(self):
        for book in self.books[:3]:
            self.hold(self.bo, book)
        self.assertError(Conflict, "member", "hold.place", book=self.books[3], member=self.bo)

    def test_a_ready_hold_still_counts(self):
        for book in self.books[:3]:
            self.hold(self.bo, book)
        self.give_back()
        self.assertError(Conflict, "member", "hold.place", book=self.books[3], member=self.bo)

    def test_cancelled_holds_do_not_count(self):
        ids = [self.hold(self.bo, book)["id"] for book in self.books[:3]]
        self.call("hold.cancel", hold=ids[0])
        self.assertEqual(self.hold(self.bo, self.books[3])["status"], "waiting")

    def test_collected_holds_do_not_count(self):
        for book in self.books[:3]:
            self.hold(self.bo, book)
        self.give_back()
        self.call("hold.collect", hold="hold_0001")
        self.assertEqual(self.hold(self.bo, self.books[3])["status"], "waiting")
        self.assertError(Conflict, "member", "hold.place", book=self.books[4], member=self.bo)

    def test_expired_holds_do_not_count(self):
        for book in self.books[:3]:
            self.hold(self.bo, book)
        self.give_back()
        self.clock.advance(hours=72)
        self.assertEqual(self.hold(self.bo, self.books[3])["status"], "waiting")


class TestShelf(Base):
    """answers.json: shelf"""

    def test_a_book_on_the_shelf_cannot_be_held(self):
        self.assertError(Conflict, "book", "hold.place", book=self.books[1], member=self.bo)
        self.assertEqual(self.svc.bus.log, [])

    def test_a_book_reserved_by_a_ready_hold_can_be_held(self):
        self.hold(self.bo)
        self.give_back()
        h = self.hold(self.cy)
        self.assertEqual(h["status"], "waiting")

    def test_a_lapsed_book_with_nobody_else_is_on_the_shelf_again(self):
        self.hold(self.bo)
        self.give_back()
        self.clock.advance(hours=72)
        self.assertError(Conflict, "book", "hold.place", book=self.dune, member=self.cy)


class TestSameMember(Base):
    """answers.json: same_member"""

    def test_cannot_hold_a_book_they_have_on_loan(self):
        self.assertError(Conflict, "member", "hold.place", book=self.dune, member=self.ann)
        self.assertEqual(self.svc.bus.log, [])

    def test_cannot_hold_the_same_book_twice(self):
        self.hold(self.bo)
        self.assertError(Conflict, "member", "hold.place", book=self.dune, member=self.bo)

    def test_cannot_hold_twice_when_the_first_is_ready(self):
        self.hold(self.bo)
        self.give_back()
        self.assertError(Conflict, "member", "hold.place", book=self.dune, member=self.bo)

    def test_can_hold_again_after_cancelling(self):
        h = self.hold(self.bo)["id"]
        self.call("hold.cancel", hold=h)
        self.assertEqual(self.hold(self.bo)["id"], "hold_0002")


class TestOverdue(Base):
    """answers.json: overdue"""

    def setUp(self):
        super().setUp()
        self.cy_loan = self.borrow(self.books[1], self.cy)["id"]       # due 2026-01-19T09:00:00Z
        self.svc.bus.log.clear()

    def test_an_overdue_member_cannot_place_a_hold(self):
        self.clock.advance(days=14, seconds=1)
        self.assertError(Conflict, "member", "hold.place", book=self.dune, member=self.cy)
        self.assertEqual(self.svc.bus.log, [])

    def test_at_the_due_time_it_is_not_overdue_yet(self):
        self.clock.advance(days=14)
        self.assertEqual(self.hold(self.cy)["status"], "waiting")

    def test_a_loan_that_is_returned_no_longer_counts(self):
        self.clock.advance(days=20)
        self.call("loan.return", loan=self.cy_loan)
        self.assertEqual(self.hold(self.cy)["status"], "waiting")

    def test_going_overdue_does_not_touch_holds_already_placed(self):
        h = self.hold(self.cy)["id"]
        self.clock.advance(days=15)
        self.give_back()
        self.assertEqual(self.status(h), "ready")
        self.assertEqual(self.call("hold.collect", hold=h)["status"], "collected")


class TestRegression(Base):
    def test_existing_operations_unchanged(self):
        self.assertEqual(self.call("loan.retrieve", loan=self.ann_loan)["status"], "open")
        self.assertError(Conflict, "book", "loan.borrow", book=self.dune, member=self.bo)
        out = self.give_back()
        self.assertEqual((out["status"], out["version"]), ("returned", 2))
        self.assertError(Conflict, "loan", "loan.return", loan=self.ann_loan)
        self.assertEqual(self.borrow(self.dune, self.bo)["id"], "loan_0002")


if __name__ == "__main__":
    unittest.main()
