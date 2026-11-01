import unittest

from lendr import Service
from lendr.clock import FixedClock
from lendr.errors import Conflict, InvalidRequest, NotFound, Unavailable


class LendrTest(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.book = self.svc.call("book.create", title="Dune", copies=1)["id"]
        self.ada = self.svc.call("member.create", name="Ada")["id"]
        self.bob = self.svc.call("member.create", name="Bob")["id"]

    def test_checkout_and_return(self):
        loan = self.svc.call("loan.checkout", book=self.book, member=self.ada)
        self.assertEqual((loan["id"], loan["status"], loan["due"]), ("loan_0001", "open", "2026-01-19T09:00:00Z"))
        self.assertEqual(self.svc.call("book.retrieve", book=self.book)["available"], 0)
        with self.assertRaises(Unavailable):
            self.svc.call("loan.checkout", book=self.book, member=self.bob)
        done = self.svc.call("loan.return", loan=loan["id"])
        self.assertEqual((done["status"], done["version"]), ("returned", 2))
        self.assertEqual(self.svc.call("book.retrieve", book=self.book)["available"], 1)

    def test_late_return_charges_a_fine(self):
        loan = self.svc.call("loan.checkout", book=self.book, member=self.ada)
        self.clock.advance(days=16, hours=1)
        self.svc.call("loan.return", loan=loan["id"])
        self.assertEqual([e["type"] for e in self.svc.bus.log][-2:], ["loan.returned", "fine.charged"])
        self.assertEqual(self.svc.call("loan.fines", member=self.ada)["data"][0]["amount"], 75)

    def test_errors(self):
        with self.assertRaises(NotFound):
            self.svc.call("loan.checkout", book="book_9999", member=self.ada)
        with self.assertRaises(InvalidRequest):
            self.svc.call("book.create", title="X", copies=0)
        self.svc.call("member.suspend", member=self.bob)
        with self.assertRaises(Conflict):
            self.svc.call("loan.checkout", book=self.book, member=self.bob)

    def test_retire_returns_open_loans(self):
        self.svc.call("loan.checkout", book=self.book, member=self.ada)
        self.svc.bus.log.clear()
        self.svc.call("book.retire", book=self.book)
        self.assertEqual([e["type"] for e in self.svc.bus.log], ["book.retired", "loan.returned"])


if __name__ == "__main__":
    unittest.main()
