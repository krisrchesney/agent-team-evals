import unittest

from clinic import Service
from clinic.clock import FixedClock
from clinic.errors import Conflict, InvalidRequest, NotFound


class ClinicTest(unittest.TestCase):
    def setUp(self):
        self.svc = Service(clock=FixedClock())
        self.rae = self.svc.call("patient.create", name="Rae")["id"]
        self.kit = self.svc.call("patient.create", name="Kit")["id"]

    def book(self, patient=None, start="2026-01-12T09:00:00Z", minutes=30):
        return self.svc.call("appointment.book", patient=patient or self.rae, start=start, minutes=minutes)

    def test_appointment_view(self):
        a = self.book()
        self.assertEqual((a["id"], a["patient"], a["start"], a["end"], a["status"], a["version"]),
                         ("appointment_0001", self.rae, "2026-01-12T09:00:00Z", "2026-01-12T09:30:00Z", "booked", 1))

    def test_the_doctor_sees_one_patient_at_a_time(self):
        self.book()
        with self.assertRaises(Conflict) as ctx:
            self.book(patient=self.kit, start="2026-01-12T09:15:00Z")
        self.assertEqual(ctx.exception.param, "start")
        self.book(patient=self.kit, start="2026-01-12T09:30:00Z")

    def test_bad_input(self):
        for kw, param in (({"start": "soon"}, "start"), ({"start": "2026-01-05T09:00:00Z"}, "start"),
                          ({"minutes": 0}, "minutes"), ({"minutes": 241}, "minutes")):
            with self.subTest(**kw):
                with self.assertRaises(InvalidRequest) as ctx:
                    self.book(**kw)
                self.assertEqual(ctx.exception.param, param)

    def test_cancel_frees_the_slot(self):
        a = self.book()
        out = self.svc.call("appointment.cancel", appointment=a["id"])
        self.assertEqual((out["status"], out["version"]), ("cancelled", 2))
        self.book(patient=self.kit)
        with self.assertRaises(Conflict) as ctx:
            self.svc.call("appointment.cancel", appointment=a["id"])
        self.assertEqual(ctx.exception.param, "appointment")

    def test_unknown_patient_and_list_order(self):
        with self.assertRaises(NotFound) as ctx:
            self.book(patient="patient_9999")
        self.assertEqual(ctx.exception.param, "patient")
        self.book(start="2026-01-13T09:00:00Z")
        self.book(start="2026-01-12T09:00:00Z")
        rows = self.svc.call("appointment.list", patient=self.rae)["data"]
        self.assertEqual([r["start"][:10] for r in rows], ["2026-01-12", "2026-01-13"])
