import unittest

from rota import Service
from rota.clock import FixedClock
from rota.errors import Conflict, InvalidRequest, NotFound


class RotaTest(unittest.TestCase):
    def setUp(self):
        self.svc = Service(clock=FixedClock())
        self.mara = self.svc.call("staff.create", name="Mara")["id"]
        self.shift = self.svc.call("shift.create", staff=self.mara, start="2026-01-12T09:00:00Z",
                                   end="2026-01-12T17:00:00Z")

    def test_shift_view(self):
        s = self.shift
        self.assertEqual((s["id"], s["staff"], s["start"], s["end"], s["version"]),
                         ("shift_0001", self.mara, "2026-01-12T09:00:00Z", "2026-01-12T17:00:00Z", 1))

    def test_overlap_is_a_conflict(self):
        with self.assertRaises(Conflict) as ctx:
            self.svc.call("shift.create", staff=self.mara, start="2026-01-12T16:00:00Z", end="2026-01-12T20:00:00Z")
        self.assertEqual(ctx.exception.param, "start")

    def test_back_to_back_is_fine(self):
        self.svc.call("shift.create", staff=self.mara, start="2026-01-12T17:00:00Z", end="2026-01-12T20:00:00Z")

    def test_bad_times(self):
        for start, end, param in (("soon", "2026-01-12T20:00:00Z", "start"),
                                  ("2026-01-13T09:00:00Z", "2026-01-13T09:00:00Z", "end"),
                                  ("2026-01-13T00:00:00Z", "2026-01-13T17:00:01Z", "end")):
            with self.subTest(start=start, end=end):
                with self.assertRaises(InvalidRequest) as ctx:
                    self.svc.call("shift.create", staff=self.mara, start=start, end=end)
                self.assertEqual(ctx.exception.param, param)

    def test_unknown_staff(self):
        with self.assertRaises(NotFound) as ctx:
            self.svc.call("shift.list", staff="staff_9999")
        self.assertEqual(ctx.exception.param, "staff")

    def test_list_in_time_order(self):
        self.svc.call("shift.create", staff=self.mara, start="2026-01-11T09:00:00Z", end="2026-01-11T10:00:00Z")
        rows = self.svc.call("shift.list", staff=self.mara)["data"]
        self.assertEqual([r["start"][:10] for r in rows], ["2026-01-11", "2026-01-12"])
