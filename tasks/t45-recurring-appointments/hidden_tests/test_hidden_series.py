"""Hidden tests for t45-recurring-appointments. Rules come from the prompt, the repo, or answers.json; see AUDIT.md."""
import unittest

from clinic import Service
from clinic.clock import FixedClock
from clinic.errors import ClinicError, Conflict, InvalidRequest, NotFound

T0 = "2026-01-05T09:00:00Z"
WEEKLY = ["2026-01-12T10:00:00Z", "2026-01-19T10:00:00Z", "2026-01-26T10:00:00Z", "2026-02-02T10:00:00Z"]


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock()                      # 2026-01-05T09:00:00Z
        self.svc = Service(clock=self.clock)
        self.rae = self.svc.call("patient.create", name="Rae")["id"]
        self.kit = self.svc.call("patient.create", name="Kit")["id"]
        self.svc.bus.log.clear()

    def call(self, op, **params):
        return self.svc.call(op, **params)

    def series(self, start="2026-01-12T10:00:00Z", repeat="weekly", count=4, patient=None, minutes=30):
        return self.call("series.create", patient=patient or self.rae, start=start, minutes=minutes,
                         repeat=repeat, count=count)

    def book(self, start, patient=None, minutes=30):
        return self.call("appointment.book", patient=patient or self.kit, start=start, minutes=minutes)

    def appt(self, appointment_id):
        return self.call("appointment.retrieve", appointment=appointment_id)

    def starts(self, series):
        return [self.appt(a)["start"] for a in series["appointments"]]

    def statuses(self, series):
        return [self.appt(a)["status"] for a in series["appointments"]]

    def assertError(self, cls, param, op, **params):
        with self.assertRaises(cls) as ctx:
            self.call(op, **params)
        self.assertIsInstance(ctx.exception, ClinicError)
        self.assertEqual(ctx.exception.param, param)
        return ctx.exception


class TestCreate(Base):
    def test_operations_are_registered(self):
        ops = set(self.svc.operations())
        self.assertTrue({"series.create", "series.cancel", "series.retrieve"} <= ops)
        self.assertTrue({"appointment.book", "patient.create"} <= ops)

    def test_series_view(self):
        s = self.series()
        self.assertEqual(s["id"], "series_0001")
        self.assertEqual((s["patient"], s["repeat"], s["status"]), (self.rae, "weekly", "active"))
        self.assertEqual((s["created_at"], s["updated_at"], s["version"]), (T0, T0, 1))
        self.assertEqual(s["appointments"], [f"appointment_{n:04d}" for n in range(1, 5)])

    def test_the_appointments_are_real(self):
        s = self.series(minutes=45)
        self.assertEqual(self.starts(s), WEEKLY)
        a = self.appt(s["appointments"][1])
        self.assertEqual((a["patient"], a["end"], a["status"], a["version"], a["created_at"]),
                         (self.rae, "2026-01-19T10:45:00Z", "booked", 1, T0))
        self.assertEqual(len(self.call("appointment.list", patient=self.rae)["data"]), 4)

    def test_create_event(self):
        s = self.series()
        self.assertEqual(self.svc.bus.log, [{"type": "series.created", "data": {"series": s}}])

    def test_unknown_and_missing_arguments(self):
        self.assertError(NotFound, "patient", "series.create", patient="patient_9999", start=WEEKLY[0],
                         minutes=30, repeat="weekly", count=3)
        self.assertError(InvalidRequest, "patient", "series.create", start=WEEKLY[0], minutes=30,
                         repeat="weekly", count=3)
        self.assertError(InvalidRequest, "start", "series.create", patient=self.rae, minutes=30,
                         repeat="weekly", count=3)
        self.assertError(InvalidRequest, "minutes", "series.create", patient=self.rae, start=WEEKLY[0],
                         repeat="weekly", count=3)

    def test_the_first_slot_must_be_in_the_future(self):
        self.assertError(InvalidRequest, "start", "series.create", patient=self.rae, start="2026-01-05T09:00:00Z",
                         minutes=30, repeat="weekly", count=3)
        self.assertError(InvalidRequest, "start", "series.create", patient=self.rae, start="soon",
                         minutes=30, repeat="weekly", count=3)

    def test_failures_change_nothing(self):
        with self.assertRaises(ClinicError):
            self.series(patient="patient_9999")
        self.assertEqual(self.svc.bus.log, [])
        self.assertEqual(self.call("appointment.list")["data"], [])
        self.assertEqual(self.series()["id"], "series_0001")

    def test_retrieve(self):
        s = self.series()
        self.svc.bus.log.clear()
        self.assertEqual(self.call("series.retrieve", series=s["id"]), s)
        self.assertEqual(self.svc.bus.log, [])
        self.assertError(NotFound, "series", "series.retrieve", series="series_9999")
        self.assertError(InvalidRequest, "series", "series.retrieve")


class TestMonthEnd(Base):
    """answers.json: month_end"""

    def test_the_31st(self):
        s = self.series(start="2026-01-31T10:00:00Z", repeat="monthly", count=4)
        self.assertEqual(self.starts(s), ["2026-01-31T10:00:00Z", "2026-02-28T10:00:00Z",
                                          "2026-03-31T10:00:00Z", "2026-04-30T10:00:00Z"])

    def test_the_29th_and_30th(self):
        s = self.series(start="2026-01-29T10:00:00Z", repeat="monthly", count=3)
        self.assertEqual(self.starts(s), ["2026-01-29T10:00:00Z", "2026-02-28T10:00:00Z", "2026-03-29T10:00:00Z"])
        t = self.series(start="2026-01-30T11:00:00Z", repeat="monthly", count=3, patient=self.kit)
        self.assertEqual(self.starts(t), ["2026-01-30T11:00:00Z", "2026-02-28T11:00:00Z", "2026-03-30T11:00:00Z"])

    def test_leap_year(self):
        s = self.series(start="2028-01-31T10:00:00Z", repeat="monthly", count=3)
        self.assertEqual(self.starts(s), ["2028-01-31T10:00:00Z", "2028-02-29T10:00:00Z", "2028-03-31T10:00:00Z"])

    def test_across_the_new_year(self):
        s = self.series(start="2026-11-30T10:00:00Z", repeat="monthly", count=4)
        self.assertEqual(self.starts(s), ["2026-11-30T10:00:00Z", "2026-12-30T10:00:00Z",
                                          "2027-01-30T10:00:00Z", "2027-02-28T10:00:00Z"])

    def test_an_ordinary_day_stays_put(self):
        s = self.series(start="2026-01-15T08:30:00Z", repeat="monthly", count=3)
        self.assertEqual(self.starts(s), ["2026-01-15T08:30:00Z", "2026-02-15T08:30:00Z", "2026-03-15T08:30:00Z"])

    def test_no_month_is_skipped(self):
        s = self.series(start="2026-01-31T10:00:00Z", repeat="monthly", count=12, patient=self.rae)
        self.assertEqual(len(s["appointments"]), 12)
        self.assertEqual(self.starts(s)[-1], "2026-12-31T10:00:00Z")


class TestClashes(Base):
    """answers.json: clashes"""

    def test_a_clashing_occurrence_is_skipped(self):
        self.book("2026-01-19T10:00:00Z")                         # Kit, appointment_0001
        s = self.series()
        self.assertEqual(self.starts(s), [WEEKLY[0], WEEKLY[2], WEEKLY[3]])
        self.assertEqual(s["skipped"], [WEEKLY[1]])
        self.assertEqual(s["appointments"], ["appointment_0002", "appointment_0003", "appointment_0004"])

    def test_nothing_skipped_is_an_empty_list(self):
        self.assertEqual(self.series()["skipped"], [])

    def test_partial_overlap_clashes_but_touching_does_not(self):
        self.book("2026-01-19T10:15:00Z")                         # overlaps 10:00-10:30
        self.book("2026-01-26T10:30:00Z")                         # starts as the occurrence ends
        s = self.series()
        self.assertEqual(s["skipped"], [WEEKLY[1]])
        self.assertEqual(len(s["appointments"]), 3)

    def test_skipped_ones_are_listed_in_date_order(self):
        self.book("2026-02-02T10:00:00Z")
        self.book("2026-01-19T10:00:00Z")
        s = self.series()
        self.assertEqual(s["skipped"], [WEEKLY[1], WEEKLY[3]])
        self.assertEqual(self.starts(s), [WEEKLY[0], WEEKLY[2]])

    def test_a_cancelled_appointment_does_not_clash(self):
        gone = self.book("2026-01-19T10:00:00Z")["id"]
        self.call("appointment.cancel", appointment=gone)
        self.assertEqual(self.series()["skipped"], [])

    def test_a_clash_on_the_first_one_refuses_everything(self):
        self.book("2026-01-12T10:00:00Z")
        self.svc.bus.log.clear()
        self.assertError(Conflict, "start", "series.create", patient=self.rae, start=WEEKLY[0], minutes=30,
                         repeat="weekly", count=4)
        self.assertEqual(self.svc.bus.log, [])
        self.assertEqual(len(self.call("appointment.list")["data"]), 1)
        self.assertEqual(self.series(start="2026-01-13T10:00:00Z")["appointments"], ["appointment_0002", "appointment_0003",
                                                                                  "appointment_0004", "appointment_0005"])

    def test_only_the_first_can_be_booked(self):
        for start in WEEKLY[1:]:
            self.book(start)
        s = self.series()
        self.assertEqual(len(s["appointments"]), 1)
        self.assertEqual(s["skipped"], WEEKLY[1:])

    def test_skipped_slots_stay_free(self):
        self.book("2026-01-19T10:00:00Z")
        self.series()
        self.assertEqual(len([a for a in self.call("appointment.list")["data"] if a["start"] == WEEKLY[1]]), 1)


class TestCount(Base):
    """answers.json: count"""

    def test_two_and_twelve_are_fine(self):
        self.assertEqual(len(self.series(count=2)["appointments"]), 2)
        self.assertEqual(len(self.series(count=12, start="2026-06-01T10:00:00Z", patient=self.kit)["appointments"]), 12)

    def test_one_and_thirteen_are_refused(self):
        for count in (1, 13, 0, -3):
            with self.subTest(count=count):
                self.assertError(InvalidRequest, "count", "series.create", patient=self.rae, start=WEEKLY[0],
                                 minutes=30, repeat="weekly", count=count)

    def test_count_must_be_a_whole_number(self):
        for count in (4.0, "4", True, None):
            with self.subTest(count=count):
                self.assertError(InvalidRequest, "count", "series.create", patient=self.rae, start=WEEKLY[0],
                                 minutes=30, repeat="weekly", count=count)
        self.assertError(InvalidRequest, "count", "series.create", patient=self.rae, start=WEEKLY[0],
                         minutes=30, repeat="weekly")

    def test_repeat_must_be_weekly_or_monthly(self):
        for repeat in ("daily", "", "Weekly", 7):
            with self.subTest(repeat=repeat):
                self.assertError(InvalidRequest, "repeat", "series.create", patient=self.rae, start=WEEKLY[0],
                                 minutes=30, repeat=repeat, count=3)
        self.assertError(InvalidRequest, "repeat", "series.create", patient=self.rae, start=WEEKLY[0],
                         minutes=30, count=3)

    def test_refusals_change_nothing(self):
        with self.assertRaises(InvalidRequest):
            self.series(count=13)
        self.assertEqual((self.svc.bus.log, self.call("appointment.list")["data"]), ([], []))


class TestCancel(Base):
    """answers.json: cancel_scope"""

    def test_cancel_a_series_before_it_starts(self):
        s = self.series()
        self.clock.advance(hours=3)
        self.svc.bus.log.clear()
        out = self.call("series.cancel", series=s["id"])
        self.assertEqual((out["status"], out["version"], out["updated_at"]), ("cancelled", 2, "2026-01-05T12:00:00Z"))
        self.assertEqual(out["appointments"], s["appointments"])
        self.assertEqual(self.statuses(out), ["cancelled"] * 4)
        a = self.appt(s["appointments"][0])
        self.assertEqual((a["version"], a["updated_at"]), (2, "2026-01-05T12:00:00Z"))
        self.assertEqual(self.svc.bus.log, [{"type": "series.cancelled", "data": {"series": out}}])

    def test_started_occurrences_stay_booked(self):
        s = self.series()
        self.clock.advance(days=14, hours=1)                       # 2026-01-19T10:00:00Z: the second one has begun
        out = self.call("series.cancel", series=s["id"])
        self.assertEqual(self.statuses(out), ["booked", "booked", "cancelled", "cancelled"])

    def test_one_second_before_the_start_still_cancels_it(self):
        s = self.series()
        self.clock.advance(days=14, hours=0, minutes=59, seconds=59)   # 2026-01-19T09:59:59Z
        out = self.call("series.cancel", series=s["id"])
        self.assertEqual(self.statuses(out), ["booked", "cancelled", "cancelled", "cancelled"])

    def test_a_series_in_the_past_cancels_nothing_but_closes(self):
        s = self.series()
        self.clock.advance(days=60)
        out = self.call("series.cancel", series=s["id"])
        self.assertEqual((out["status"], self.statuses(out)), ("cancelled", ["booked"] * 4))

    def test_an_occurrence_cancelled_earlier_is_left_alone(self):
        s = self.series()
        self.call("appointment.cancel", appointment=s["appointments"][1])
        self.clock.advance(hours=1)
        self.call("series.cancel", series=s["id"])
        a = self.appt(s["appointments"][1])
        self.assertEqual((a["status"], a["version"], a["updated_at"]), ("cancelled", 2, T0))

    def test_other_appointments_are_untouched(self):
        s = self.series()
        mine = self.book("2026-01-14T10:00:00Z", patient=self.rae)["id"]
        theirs = self.book("2026-01-13T10:00:00Z")["id"]
        self.call("series.cancel", series=s["id"])
        self.assertEqual((self.appt(mine)["status"], self.appt(theirs)["status"]), ("booked", "booked"))

    def test_the_slots_are_free_again(self):
        s = self.series()
        self.call("series.cancel", series=s["id"])
        self.assertEqual(self.book(WEEKLY[1])["status"], "booked")

    def test_cancelling_twice_is_a_conflict(self):
        s = self.series()
        self.call("series.cancel", series=s["id"])
        self.svc.bus.log.clear()
        self.assertError(Conflict, "series", "series.cancel", series=s["id"])
        self.assertEqual(self.svc.bus.log, [])

    def test_unknown_series(self):
        self.assertError(NotFound, "series", "series.cancel", series="series_9999")
        self.assertError(InvalidRequest, "series", "series.cancel")


class TestOneSeries(Base):
    """answers.json: one_series"""

    def test_a_second_series_is_refused(self):
        self.series()
        self.svc.bus.log.clear()
        self.assertError(Conflict, "patient", "series.create", patient=self.rae, start="2026-03-02T10:00:00Z",
                         minutes=30, repeat="monthly", count=3)
        self.assertEqual((self.svc.bus.log, len(self.call("appointment.list")["data"])), ([], 4))

    def test_fine_after_cancelling_the_first(self):
        s = self.series()
        self.call("series.cancel", series=s["id"])
        self.assertEqual(self.series(start="2026-03-02T10:00:00Z")["id"], "series_0002")

    def test_other_patients_are_unaffected(self):
        self.series()
        self.assertEqual(self.series(start="2026-01-13T10:00:00Z", patient=self.kit)["patient"], self.kit)


class TestRegression(Base):
    def test_existing_operations_unchanged(self):
        a = self.book("2026-01-12T09:00:00Z")
        self.assertEqual((a["id"], a["end"], a["status"]), ("appointment_0001", "2026-01-12T09:30:00Z", "booked"))
        self.assertError(Conflict, "start", "appointment.book", patient=self.rae, start="2026-01-12T09:15:00Z", minutes=30)
        out = self.call("appointment.cancel", appointment=a["id"])
        self.assertEqual((out["status"], out["version"]), ("cancelled", 2))
        self.assertError(Conflict, "appointment", "appointment.cancel", appointment=a["id"])


if __name__ == "__main__":
    unittest.main()
