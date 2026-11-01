"""Hidden tests for t40-shift-swap. Rules come from the prompt, the repo, or answers.json; see AUDIT.md."""
import unittest

from rota import Service
from rota.clock import FixedClock
from rota.errors import Conflict, InvalidRequest, NotFound, RotaError

T0 = "2026-01-05T09:00:00Z"
S_START, S_END = "2026-01-12T09:00:00Z", "2026-01-12T17:00:00Z"


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()
        self.svc = Service(clock=self.clock)
        self.mara = self.svc.call("staff.create", name="Mara")["id"]
        self.jo = self.svc.call("staff.create", name="Jo")["id"]
        self.shift = self.shift_for(self.mara, S_START, S_END)
        self.svc.bus.log.clear()

    def shift_for(self, staff, start, end):
        return self.svc.call("shift.create", staff=staff, start=start, end=end)["id"]

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def request(self, shift=None, to=None):
        return self.call("swap.request", shift=shift or self.shift, to_staff=to or self.jo)

    def holder(self, shift=None):
        return self.call("shift.retrieve", shift=shift or self.shift)["staff"]

    def assertError(self, cls, param, op, **params):
        with self.assertRaises(cls) as ctx:
            self.call(op, **params)
        self.assertIsInstance(ctx.exception, RotaError)
        self.assertEqual(ctx.exception.param, param)
        return ctx.exception


class TestRequest(Base):
    def test_operations_are_registered(self):
        ops = set(self.svc.operations())
        self.assertTrue({"swap.request", "swap.accept", "swap.decline", "swap.cancel", "swap.retrieve"} <= ops)
        self.assertTrue({"shift.create", "staff.create"} <= ops)

    def test_swap_view(self):
        s = self.request()
        self.assertEqual(s["id"], "swap_0001")
        self.assertEqual((s["shift"], s["from_staff"], s["to_staff"], s["status"]), (self.shift, self.mara, self.jo, "pending"))
        self.assertEqual((s["created_at"], s["updated_at"], s["version"]), (T0, T0, 1))
        self.assertEqual(self.request(self.shift_for(self.mara, "2026-01-14T09:00:00Z", "2026-01-14T17:00:00Z"))["id"], "swap_0002")

    def test_request_event(self):
        s = self.request()
        self.assertEqual(self.svc.bus.log, [{"type": "swap.requested", "data": {"swap": s}}])

    def test_request_changes_nothing_else(self):
        self.request()
        self.assertEqual(self.holder(), self.mara)
        self.assertEqual(self.call("shift.retrieve", shift=self.shift)["version"], 1)

    def test_unknown_shift_and_staff(self):
        self.assertError(NotFound, "shift", "swap.request", shift="shift_9999", to_staff=self.jo)
        self.assertError(NotFound, "to_staff", "swap.request", shift=self.shift, to_staff="staff_9999")

    def test_missing_arguments(self):
        self.assertError(InvalidRequest, "shift", "swap.request", to_staff=self.jo)
        self.assertError(InvalidRequest, "to_staff", "swap.request", shift=self.shift)

    def test_not_to_the_current_holder(self):
        self.assertError(InvalidRequest, "to_staff", "swap.request", shift=self.shift, to_staff=self.mara)

    def test_failures_change_nothing(self):
        for params in ({"shift": "shift_9999", "to_staff": self.jo}, {"shift": self.shift, "to_staff": self.mara}):
            with self.assertRaises(RotaError):
                self.call("swap.request", **params)
        self.assertEqual(self.svc.bus.log, [])
        self.assertEqual(self.request()["id"], "swap_0001")

    def test_retrieve(self):
        s = self.request()
        self.assertEqual(self.call("swap.retrieve", swap=s["id"]), s)
        self.assertError(NotFound, "swap", "swap.retrieve", swap="swap_9999")
        self.assertError(InvalidRequest, "swap", "swap.retrieve")


class TestResolve(Base):
    def test_accept_hands_over_the_shift(self):
        self.request()
        self.clock.advance(hours=3)
        s = self.call("swap.accept", swap="swap_0001")
        self.assertEqual((s["status"], s["version"], s["updated_at"]), ("accepted", 2, "2026-01-05T12:00:00Z"))
        sh = self.call("shift.retrieve", shift=self.shift)
        self.assertEqual((sh["staff"], sh["version"], sh["updated_at"]), (self.jo, 2, "2026-01-05T12:00:00Z"))
        self.assertEqual([x["id"] for x in self.call("shift.list", staff=self.jo)["data"]], [self.shift])
        self.assertEqual(self.call("shift.list", staff=self.mara)["data"], [])

    def test_accept_event(self):
        self.request()
        self.svc.bus.log.clear()
        s = self.call("swap.accept", swap="swap_0001")
        (ev,) = self.svc.bus.log
        self.assertEqual(ev["type"], "swap.accepted")
        self.assertEqual(ev["data"]["swap"], s)
        self.assertEqual(ev["data"]["shift"], self.call("shift.retrieve", shift=self.shift))

    def test_decline_and_cancel_leave_the_shift(self):
        for op, status, event in (("swap.decline", "declined", "swap.declined"), ("swap.cancel", "cancelled", "swap.cancelled")):
            with self.subTest(op=op):
                sh = self.shift_for(self.mara, "2026-02-0%dT09:00:00Z" % (1 if op == "swap.decline" else 2),
                                    "2026-02-0%dT17:00:00Z" % (1 if op == "swap.decline" else 2))
                s = self.request(sh)
                self.svc.bus.log.clear()
                out = self.call(op, swap=s["id"])
                self.assertEqual((out["status"], out["version"]), (status, 2))
                self.assertEqual(self.holder(sh), self.mara)
                self.assertEqual(self.svc.bus.log, [{"type": event, "data": {"swap": out}}])

    def test_cannot_resolve_twice(self):
        self.request()
        self.call("swap.decline", swap="swap_0001")
        for op in ("swap.accept", "swap.decline", "swap.cancel"):
            with self.subTest(op=op):
                self.assertError(Conflict, "swap", op, swap="swap_0001")

    def test_unknown_swap(self):
        for op in ("swap.accept", "swap.decline", "swap.cancel"):
            with self.subTest(op=op):
                self.assertError(NotFound, "swap", op, swap="swap_9999")
                self.assertError(InvalidRequest, "swap", op)

    def test_conflict_changes_nothing(self):
        self.request()
        self.call("swap.cancel", swap="swap_0001")
        self.svc.bus.log.clear()
        with self.assertRaises(Conflict):
            self.call("swap.accept", swap="swap_0001")
        self.assertEqual(self.svc.bus.log, [])
        self.assertEqual(self.call("swap.retrieve", swap="swap_0001")["version"], 2)
        self.assertEqual(self.holder(), self.mara)


class TestNotice(Base):
    """answers.json: notice"""

    def test_exactly_24_hours_is_fine(self):
        self.clock.advance(days=6, hours=0)                 # 2026-01-11T09:00Z, 24h before the shift
        self.assertEqual(self.request()["status"], "pending")

    def test_one_second_short_is_a_conflict(self):
        self.clock.advance(days=6, seconds=1)
        self.assertError(Conflict, "shift", "swap.request", shift=self.shift, to_staff=self.jo)
        self.assertEqual(self.svc.bus.log, [])

    def test_started_shift_is_a_conflict(self):
        self.clock.advance(days=7, hours=1)
        self.assertError(Conflict, "shift", "swap.request", shift=self.shift, to_staff=self.jo)

    def test_notice_is_not_rechecked_later(self):
        self.clock.advance(days=5)                          # 2026-01-10T09:00Z, 48h before the shift
        self.request()
        self.clock.advance(hours=30)                        # under 24h to go, the swap is still pending
        self.assertEqual(self.call("swap.accept", swap="swap_0001")["status"], "accepted")

    def test_notice_counts_from_the_shift_start_not_end(self):
        sh = self.shift_for(self.mara, "2026-01-07T07:00:00Z", "2026-01-07T17:00:00Z")   # starts in 46h
        self.assertEqual(self.request(sh)["shift"], sh)


class TestLapse(Base):
    """answers.json: lapse"""

    def test_expires_after_48_hours(self):
        s = self.request()
        self.assertEqual(s["expires_at"], "2026-01-07T09:00:00Z")
        self.clock.advance(hours=47, minutes=59, seconds=59)
        self.assertEqual(self.call("swap.retrieve", swap=s["id"])["status"], "pending")

    def test_expired_at_the_moment_itself(self):
        s = self.request()
        self.clock.advance(hours=48)
        self.assertEqual(self.call("swap.retrieve", swap=s["id"])["status"], "expired")

    def test_lapses_at_shift_start_if_sooner(self):
        sh = self.shift_for(self.mara, "2026-01-06T20:00:00Z", "2026-01-06T22:00:00Z")   # in 35h
        s = self.request(sh)
        self.assertEqual(s["expires_at"], "2026-01-06T20:00:00Z")
        self.clock.advance(hours=35)
        self.assertEqual(self.call("swap.retrieve", swap=s["id"])["status"], "expired")

    def test_expired_cannot_be_resolved(self):
        self.request()
        self.clock.advance(hours=49)
        for op in ("swap.accept", "swap.decline", "swap.cancel"):
            with self.subTest(op=op):
                self.assertError(Conflict, "swap", op, swap="swap_0001")
        self.assertEqual(self.holder(), self.mara)

    def test_expiry_shows_in_every_read_and_write(self):
        self.request()
        self.clock.advance(hours=49)
        self.assertEqual(self.request()["id"], "swap_0002")           # request first sees the old one expire
        self.assertEqual(self.call("swap.retrieve", swap="swap_0001")["status"], "expired")

    def test_expiry_emits_no_event(self):
        self.request()
        self.svc.bus.log.clear()
        self.clock.advance(hours=49)
        self.call("swap.retrieve", swap="swap_0001")
        self.assertEqual(self.svc.bus.log, [])

    def test_resolved_swaps_never_expire(self):
        self.request()
        self.call("swap.decline", swap="swap_0001")
        self.clock.advance(days=3)
        self.assertEqual(self.call("swap.retrieve", swap="swap_0001")["status"], "declined")


class TestRest(Base):
    """answers.json: rest"""

    def test_exactly_10_hours_is_fine(self):
        self.shift_for(self.jo, "2026-01-11T21:00:00Z", "2026-01-11T23:00:00Z")  # ends 10h before 09:00
        self.request()
        self.assertEqual(self.call("swap.accept", swap="swap_0001")["status"], "accepted")

    def test_less_than_10_hours_before(self):
        self.shift_for(self.jo, "2026-01-11T21:00:01Z", "2026-01-11T23:00:01Z")
        self.request()
        self.assertError(Conflict, "to_staff", "swap.accept", swap="swap_0001")

    def test_less_than_10_hours_after(self):
        self.shift_for(self.jo, "2026-01-13T02:00:00Z", "2026-01-13T08:00:00Z")      # starts 9h after 17:00
        self.request()
        self.assertError(Conflict, "to_staff", "swap.accept", swap="swap_0001")

    def test_exactly_10_hours_after_is_fine(self):
        self.shift_for(self.jo, "2026-01-13T03:00:00Z", "2026-01-13T08:00:00Z")
        self.request()
        self.assertEqual(self.call("swap.accept", swap="swap_0001")["status"], "accepted")

    def test_overlap_is_refused(self):
        self.shift_for(self.jo, "2026-01-12T12:00:00Z", "2026-01-12T20:00:00Z")
        self.request()
        self.assertError(Conflict, "to_staff", "swap.accept", swap="swap_0001")

    def test_back_to_back_is_refused(self):
        self.shift_for(self.jo, "2026-01-12T17:00:00Z", "2026-01-12T20:00:00Z")
        self.request()
        self.assertError(Conflict, "to_staff", "swap.accept", swap="swap_0001")

    def test_far_away_shifts_do_not_matter(self):
        self.shift_for(self.jo, "2026-01-10T09:00:00Z", "2026-01-10T17:00:00Z")
        self.shift_for(self.jo, "2026-01-14T09:00:00Z", "2026-01-14T17:00:00Z")
        self.request()
        self.assertEqual(self.call("swap.accept", swap="swap_0001")["status"], "accepted")

    def test_only_checked_on_accept(self):
        self.shift_for(self.jo, "2026-01-12T12:00:00Z", "2026-01-12T20:00:00Z")
        self.assertEqual(self.request()["status"], "pending")

    def test_refused_accept_leaves_everything(self):
        self.shift_for(self.jo, "2026-01-12T12:00:00Z", "2026-01-12T20:00:00Z")
        self.request()
        self.svc.bus.log.clear()
        with self.assertRaises(Conflict):
            self.call("swap.accept", swap="swap_0001")
        self.assertEqual(self.call("swap.retrieve", swap="swap_0001")["status"], "pending")
        self.assertEqual((self.holder(), self.call("shift.retrieve", shift=self.shift)["version"]), (self.mara, 1))
        self.assertEqual(self.svc.bus.log, [])

    def test_can_be_declined_after_a_refused_accept(self):
        self.shift_for(self.jo, "2026-01-12T12:00:00Z", "2026-01-12T20:00:00Z")
        self.request()
        with self.assertRaises(Conflict):
            self.call("swap.accept", swap="swap_0001")
        self.assertEqual(self.call("swap.decline", swap="swap_0001")["status"], "declined")

    def test_the_shift_itself_is_ignored(self):
        # the swapped shift stays on the holder's list until accepted; it must not count against the taker
        third = self.svc.call("staff.create", name="Kit")["id"]
        self.request(to=third)
        self.assertEqual(self.call("swap.accept", swap="swap_0001")["status"], "accepted")


class TestOnePending(Base):
    """answers.json: one_pending"""

    def test_second_request_refused(self):
        self.request()
        third = self.svc.call("staff.create", name="Kit")["id"]
        self.assertError(Conflict, "shift", "swap.request", shift=self.shift, to_staff=third)
        self.assertError(Conflict, "shift", "swap.request", shift=self.shift, to_staff=self.jo)

    def test_old_request_is_not_replaced(self):
        first = self.request()
        third = self.svc.call("staff.create", name="Kit")["id"]
        with self.assertRaises(Conflict):
            self.request(to=third)
        self.assertEqual(self.call("swap.retrieve", swap=first["id"])["status"], "pending")
        self.assertEqual(len([e for e in self.svc.bus.log if e["type"] == "swap.requested"]), 1)

    def test_other_shifts_are_independent(self):
        self.request()
        other = self.shift_for(self.mara, "2026-01-14T09:00:00Z", "2026-01-14T17:00:00Z")
        self.assertEqual(self.request(other)["id"], "swap_0002")

    def test_free_again_after_each_way_out(self):
        for op in ("swap.decline", "swap.cancel", "swap.accept"):
            with self.subTest(op=op):
                s = self.request()
                self.call(op, swap=s["id"])
        self.assertEqual(self.holder(), self.jo)

    def test_free_again_after_expiry(self):
        self.request()
        self.clock.advance(hours=48)
        self.assertEqual(self.request()["id"], "swap_0002")


class TestRegression(Base):
    def test_existing_operations_unchanged(self):
        self.assertEqual(self.call("shift.retrieve", shift=self.shift)["staff"], self.mara)
        self.assertEqual(len(self.call("shift.list")["data"]), 1)
        with self.assertRaises(Conflict):
            self.shift_for(self.mara, "2026-01-12T16:00:00Z", "2026-01-12T20:00:00Z")


if __name__ == "__main__":
    unittest.main()
