import unittest
from datetime import datetime

from sched.clock import FixedClock
from sched.errors import Conflict, InvalidTime
from sched.service import Scheduler


class SchedTest(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock(datetime(2026, 3, 2, 8, 0))
        self.s = Scheduler(clock=self.clock)
        self.s.add_user("ann", "Ann")
        self.s.add_user("ben", "Ben", hours={"mon": ["10:00", "14:00"]})
        self.cal = self.s.create_calendar("Team")["id"]

    def standup(self, **kw):
        args = dict(calendar=self.cal, title="Standup", start="2026-03-02T09:00", duration="30m",
                    attendees=["ann", "ben"])
        args.update(kw)
        return self.s.create_event(**args)

    def test_create_event_view(self):
        ev = self.standup()
        self.assertEqual((ev["id"], ev["start"], ev["end"], ev["duration"]),
                         ("ev1", "2026-03-02T09:00+00:00", "2026-03-02T09:30+00:00", "30m"))

    def test_bad_input(self):
        with self.assertRaises(InvalidTime):
            self.standup(start="next tuesday")

    def test_daily_rule_with_skip(self):
        ev = self.standup(rule={"freq": "daily", "count": 4})
        self.s.skip_occurrence(ev["id"], "2026-03-03")
        starts = [o["start"] for o in self.s.occurrences(ev["id"], "2026-03-02T00:00", "2026-03-10T00:00")]
        self.assertEqual(starts, ["2026-03-02T09:00+00:00", "2026-03-04T09:00+00:00", "2026-03-05T09:00+00:00"])

    def test_weekly_and_monthly_rules(self):
        weekly = self.standup(rule={"freq": "weekly", "weekdays": ["mon", "wed"], "count": 3})
        got = [o["start"][:10] for o in self.s.occurrences(weekly["id"], "2026-03-01T00:00", "2026-04-01T00:00")]
        self.assertEqual(got, ["2026-03-02", "2026-03-04", "2026-03-09"])
        monthly = self.standup(start="2026-01-31T09:00", rule={"freq": "monthly", "count": 3})
        got = [o["start"][:10] for o in self.s.occurrences(monthly["id"], "2026-01-01T00:00", "2026-12-31T00:00")]
        self.assertEqual(got, ["2026-01-31", "2026-02-28", "2026-03-31"])

    def test_reminders(self):
        self.standup(remind=[10, 60])
        self.clock.advance(hours=1, minutes=15)          # 09:15
        due = self.s.reminders_due("2026-03-02T08:00")
        self.assertEqual([(d["minutes"], d["fire_at"]) for d in due],
                         [(10, "2026-03-02T08:50+00:00")])

    def test_free_slots_use_working_hours(self):
        slots = self.s.free_slots(["ann", "ben"], "2026-03-02", "1h")
        self.assertEqual(slots[0], {"start": "2026-03-02T10:00+00:00", "end": "2026-03-02T11:00+00:00"})
        self.assertEqual(slots[-1]["start"], "2026-03-02T13:00+00:00")
        self.assertEqual(self.s.free_slots(["ann"], "2026-03-01", "1h"), [])

    def test_booking_conflict_and_outside_hours(self):
        self.standup(start="2026-03-02T10:00")
        with self.assertRaises(Conflict):
            self.s.book(self.cal, "Sync", "2026-03-02T10:15", "30m", ["ben"])
        out = self.s.book(self.cal, "Late", "2026-03-02T13:30", "1h", ["ann", "ben"])
        self.assertEqual(out["outside_hours"], ["ben"])

    def test_agenda_and_digest(self):
        self.standup()
        self.s.create_event(self.cal, "Review", "2026-03-02T15:00", "1h30m", attendees=["ann"])
        self.assertEqual([i["title"] for i in self.s.agenda_for("ann", "2026-03-02")], ["Standup", "Review"])
        self.assertEqual(self.s.digest("ann", "2026-03-02"),
                         "Ann - Mon 02 Mar\n09:00-09:30 Standup\n15:00-16:30 Review")
        self.assertEqual(self.s.digest("ben", "2026-03-03"), "Ben - Tue 03 Mar\nNo events.")
        self.assertEqual(len(self.s.week_for("ann", "2026-03-02")), 7)

    def test_ics_export(self):
        self.standup(rule={"freq": "daily", "count": 2})
        text = self.s.export_ics(self.cal)
        self.assertIn("DTSTART:20260302T090000Z\r\n", text)
        self.assertIn("RRULE:FREQ=DAILY;INTERVAL=1;COUNT=2\r\n", text)
        self.assertIn("DTSTAMP:20260302T080000Z\r\n", text)

    def test_cancel_and_move(self):
        ev = self.standup()
        self.s.move_event(ev["id"], "2026-03-02T11:00")
        self.assertEqual(self.s.get_event(ev["id"])["start"], "2026-03-02T11:00+00:00")
        self.s.cancel_event(ev["id"])
        self.assertEqual(self.s.agenda_for("ann", "2026-03-02"), [])

    def test_snapshot_round_trip(self):
        self.standup(rule={"freq": "daily", "count": 2}, remind=[15])
        self.s.skip_occurrence("ev1", "2026-03-03")
        copy = Scheduler.load(self.s.dump(), clock=self.clock)
        self.assertEqual(copy.get_event("ev1"), self.s.get_event("ev1"))
        self.assertEqual(copy.directory.get("ben").hours, self.s.directory.get("ben").hours)


if __name__ == "__main__":
    unittest.main()
