import unittest

from lending import Service
from lending.clock import FixedClock
from lending.errors import Conflict, InvalidRequest, NotFound


class LendingTest(unittest.TestCase):
    def setUp(self):
        self.svc = Service(clock=FixedClock())
        self.ann = self.svc.call("member.create", name="Ann")["id"]
        self.bo = self.svc.call("member.create", name="Bo")["id"]
        self.dune = self.svc.call("book.create", title="Dune")["id"]

    def test_borrow_view(self):
        loan = self.svc.call("loan.borrow", book=self.dune, member=self.ann)
        self.assertEqual((loan["id"], loan["book"], loan["member"], loan["status"], loan["version"]),
                         ("loan_0001", self.dune, self.ann, "open", 1))
        self.assertEqual(loan["due"], "2026-01-19T09:00:00Z")

    def test_a_book_out_cannot_be_borrowed(self):
        self.svc.call("loan.borrow", book=self.dune, member=self.ann)
        with self.assertRaises(Conflict) as ctx:
            self.svc.call("loan.borrow", book=self.dune, member=self.bo)
        self.assertEqual(ctx.exception.param, "book")

    def test_return_then_borrow_again(self):
        loan = self.svc.call("loan.borrow", book=self.dune, member=self.ann)
        out = self.svc.call("loan.return", loan=loan["id"])
        self.assertEqual((out["status"], out["version"]), ("returned", 2))
        self.svc.call("loan.borrow", book=self.dune, member=self.bo)

    def test_return_twice_is_a_conflict(self):
        loan = self.svc.call("loan.borrow", book=self.dune, member=self.ann)
        self.svc.call("loan.return", loan=loan["id"])
        with self.assertRaises(Conflict) as ctx:
            self.svc.call("loan.return", loan=loan["id"])
        self.assertEqual(ctx.exception.param, "loan")

    def test_unknown_ids(self):
        with self.assertRaises(NotFound) as ctx:
            self.svc.call("loan.borrow", book="book_9999", member=self.ann)
        self.assertEqual(ctx.exception.param, "book")
        with self.assertRaises(InvalidRequest) as ctx:
            self.svc.call("loan.borrow", book=self.dune)
        self.assertEqual(ctx.exception.param, "member")

    def test_events(self):
        loan = self.svc.call("loan.borrow", book=self.dune, member=self.ann)
        self.assertEqual(self.svc.bus.log[-1], {"type": "loan.borrowed", "data": {"loan": loan}})
