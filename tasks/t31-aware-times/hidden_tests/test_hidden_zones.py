"""Hidden tests for t31-aware-times. Test names carry the requirement number; see AUDIT.md."""
import json
import unittest
from datetime import datetime, timedelta, timezone

from sched.clock import FixedClock, SystemClock
from sched.errors import Conflict, InvalidTime, InvalidZone
from sched.service import Scheduler

UTC = timezone.utc


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock(datetime(2026, 3, 1, 8, 0, tzinfo=UTC))
        self.s = Scheduler(clock=self.clock)
        self.s.add_user("ann", "Ann", tz="America/New_York")
        self.s.add_user("ben", "Ben", tz="Europe/Berlin")
        self.s.add_user("cy", "Cy", tz="Asia/Kolkata")
        self.s.add_user("dee", "Dee")
        self.ny = self.s.create_calendar("NY", "America/New_York")["id"]
        self.berlin = self.s.create_calendar("Berlin", "Europe/Berlin")["id"]
        self.kol = self.s.create_calendar("Kolkata", "Asia/Kolkata")["id"]
        self.utc = self.s.create_calendar("UTC")["id"]

    def event(self, cal, start, duration="30m", title="Meeting", **kw):
        return self.s.create_event(cal, title, start, duration, **kw)

    def starts(self, event_id, lo, hi):
        return [o["start"] for o in self.s.occurrences(event_id, lo, hi)]


class TestZones(Base):
    def test_r1_zones_in_results(self):
        self.assertEqual(self.s.add_user("eve", "Eve", tz="Asia/Tokyo")["tz"], "Asia/Tokyo")
        self.assertEqual(self.s.add_user("fay", "Fay")["tz"], "UTC")
        self.assertEqual(self.s.create_calendar("Tokyo", "Asia/Tokyo")["tz"], "Asia/Tokyo")
        self.assertEqual(self.s.create_calendar("Plain")["tz"], "UTC")

    def test_r1_invalid_zone(self):
        for call in (lambda: self.s.add_user("zed", "Zed", tz="Mars/Base"),
                     lambda: self.s.create_calendar("Mars", "Mars/Base"),
                     lambda: self.s.create_calendar("Empty", "")):
            with self.assertRaises(InvalidZone) as ctx:
                call()
            self.assertEqual((ctx.exception.code, ctx.exception.param), ("invalid_zone", "tz"))
        self.assertEqual(len(self.s.directory.all()), 4)

    def test_r1_clocks_are_aware(self):
        self.assertEqual(FixedClock().now().utcoffset(), timedelta(0))
        self.assertEqual(FixedClock(datetime(2026, 3, 1, 9, 0)).now(), datetime(2026, 3, 1, 9, 0, tzinfo=UTC))
        clock = FixedClock(datetime(2026, 3, 1, 9, 0))
        clock.advance(hours=2)
        self.assertEqual(clock.now(), datetime(2026, 3, 1, 11, 0, tzinfo=UTC))
        self.assertEqual(SystemClock().now().utcoffset(), timedelta(0))


class TestInputAndOutput(Base):
    def test_r2_local_strings_use_the_calendar_zone(self):
        self.assertEqual(self.event(self.ny, "2026-01-12T09:00")["start"], "2026-01-12T09:00-05:00")
        self.assertEqual(self.event(self.berlin, "2026-01-12T09:00")["start"], "2026-01-12T09:00+01:00")
        self.assertEqual(self.event(self.kol, "2026-01-12T09:00")["start"], "2026-01-12T09:00+05:30")
        self.assertEqual(self.event(self.ny, "2026-07-06T09:00")["start"], "2026-07-06T09:00-04:00")
        self.assertEqual(self.event(self.utc, "2026-07-06T09:00")["start"], "2026-07-06T09:00+00:00")

    def test_r2_offsets_name_the_instant(self):
        self.assertEqual(self.event(self.ny, "2026-01-12T14:00Z")["start"], "2026-01-12T09:00-05:00")
        self.assertEqual(self.event(self.ny, "2026-01-12T15:00+01:00")["start"], "2026-01-12T09:00-05:00")
        self.assertEqual(self.event(self.berlin, "2026-01-12T14:00Z")["start"], "2026-01-12T15:00+01:00")
        self.assertEqual(self.event(self.kol, "2026-01-12T03:30:59Z")["start"], "2026-01-12T09:00+05:30")

    def test_r2_datetime_objects(self):
        aware = datetime(2026, 1, 12, 14, 0, tzinfo=UTC)
        self.assertEqual(self.event(self.ny, aware)["start"], "2026-01-12T09:00-05:00")
        ist = datetime(2026, 1, 12, 19, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        self.assertEqual(self.event(self.berlin, ist)["start"], "2026-01-12T15:00+01:00")
        self.assertEqual(self.event(self.ny, datetime(2026, 1, 12, 9, 0))["start"], "2026-01-12T09:00-05:00")

    def test_r2_bad_times(self):
        for bad in ("yesterday", "2026-13-01T09:00", "2026-01-12T09:00+25:00", "2026-01-12"):
            with self.assertRaises(InvalidTime, msg=bad) as ctx:
                self.event(self.ny, bad)
            self.assertEqual(ctx.exception.param, "start")

    def test_r2_move_event_uses_the_calendar_zone(self):
        ev = self.event(self.ny, "2026-01-12T09:00")
        self.assertEqual(self.s.move_event(ev["id"], "2026-07-06T10:00")["start"], "2026-07-06T10:00-04:00")
        self.assertEqual(self.s.move_event(ev["id"], "2026-07-06T14:00Z")["start"], "2026-07-06T10:00-04:00")

    def test_r2_occurrence_windows_use_the_calendar_zone(self):
        ev = self.event(self.ny, "2026-01-12T09:00", rule={"freq": "daily", "count": 3})
        got = self.starts(ev["id"], "2026-01-13T00:00", "2026-01-14T00:00")
        self.assertEqual(got, ["2026-01-13T09:00-05:00"])
        got = self.starts(ev["id"], "2026-01-13T14:00Z", "2026-01-13T14:01Z")
        self.assertEqual(got, ["2026-01-13T09:00-05:00"])

    def test_r3_results_are_in_the_calendar_zone(self):
        ev = self.event(self.kol, "2026-01-12T09:00", "1h30m")
        self.assertEqual((ev["start"], ev["end"], ev["duration"]),
                         ("2026-01-12T09:00+05:30", "2026-01-12T10:30+05:30", "1h30m"))
        occ = self.s.occurrences(ev["id"], "2026-01-12T00:00", "2026-01-13T00:00")
        self.assertEqual(occ, [{"start": "2026-01-12T09:00+05:30", "end": "2026-01-12T10:30+05:30"}])
        self.assertEqual(self.s.get_event(ev["id"])["start"], "2026-01-12T09:00+05:30")

    def test_reg_utc_defaults(self):
        ev = self.event(self.utc, "2026-03-02T09:00", attendees=["dee"])
        self.assertEqual((ev["start"], ev["end"]), ("2026-03-02T09:00+00:00", "2026-03-02T09:30+00:00"))
        self.assertEqual(self.s.agenda_for("dee", "2026-03-02")[0]["start"], "2026-03-02T09:00+00:00")


class TestRepeats(Base):
    def test_r4_daily_keeps_local_time_over_spring_forward(self):
        ev = self.event(self.ny, "2026-03-06T09:00", rule={"freq": "daily", "count": 5})
        got = self.starts(ev["id"], "2026-03-06T00:00", "2026-03-12T00:00")
        self.assertEqual(got, ["2026-03-06T09:00-05:00", "2026-03-07T09:00-05:00", "2026-03-08T09:00-04:00",
                               "2026-03-09T09:00-04:00", "2026-03-10T09:00-04:00"])

    def test_r4_weekly_keeps_local_time_over_fall_back_in_berlin(self):
        ev = self.event(self.berlin, "2026-10-19T09:00", rule={"freq": "weekly", "count": 3})
        got = self.starts(ev["id"], "2026-10-01T00:00", "2026-12-01T00:00")
        self.assertEqual(got, ["2026-10-19T09:00+02:00", "2026-10-26T09:00+01:00", "2026-11-02T09:00+01:00"])

    def test_r4_missing_local_time_moves_forward(self):
        ev = self.event(self.ny, "2026-03-06T02:30", rule={"freq": "daily", "count": 4})
        got = self.starts(ev["id"], "2026-03-06T00:00", "2026-03-12T00:00")
        self.assertEqual(got, ["2026-03-06T02:30-05:00", "2026-03-07T02:30-05:00", "2026-03-08T03:30-04:00",
                               "2026-03-09T02:30-04:00"])

    def test_r4_repeated_local_time_is_the_first(self):
        ev = self.event(self.ny, "2026-10-31T01:30", rule={"freq": "daily", "count": 3})
        got = self.starts(ev["id"], "2026-10-30T00:00", "2026-11-05T00:00")
        self.assertEqual(got, ["2026-10-31T01:30-04:00", "2026-11-01T01:30-04:00", "2026-11-02T01:30-05:00"])

    def test_r4_monthly_clamps_and_follows_the_clock(self):
        ev = self.event(self.ny, "2026-01-31T09:00", rule={"freq": "monthly", "count": 3})
        got = self.starts(ev["id"], "2026-01-01T00:00", "2026-12-31T00:00")
        self.assertEqual(got, ["2026-01-31T09:00-05:00", "2026-02-28T09:00-05:00", "2026-03-31T09:00-04:00"])

    def test_r4_until_and_skip_are_local_dates(self):
        ev = self.event(self.kol, "2026-01-10T02:00", rule={"freq": "daily", "until": "2026-01-14"})
        self.s.skip_occurrence(ev["id"], "2026-01-12")
        got = self.starts(ev["id"], "2026-01-09T00:00", "2026-01-20T00:00")
        self.assertEqual(got, ["2026-01-10T02:00+05:30", "2026-01-11T02:00+05:30", "2026-01-13T02:00+05:30",
                               "2026-01-14T02:00+05:30"])

    def test_r4_weekdays_are_local(self):
        ev = self.event(self.kol, "2026-01-12T01:00", rule={"freq": "weekly", "weekdays": ["mon", "wed"],
                                                           "count": 3})
        got = self.starts(ev["id"], "2026-01-01T00:00", "2026-02-01T00:00")
        self.assertEqual(got, ["2026-01-12T01:00+05:30", "2026-01-14T01:00+05:30", "2026-01-19T01:00+05:30"])

    def test_r4_lengths_are_elapsed_time(self):
        spring = self.event(self.ny, "2026-03-08T01:00", "2h")
        self.assertEqual(spring["end"], "2026-03-08T04:00-04:00")
        autumn = self.event(self.ny, "2026-11-01T00:30", "2h")
        self.assertEqual(autumn["end"], "2026-11-01T01:30-05:00")
        daily = self.event(self.ny, "2026-03-07T01:00", "2h", rule={"freq": "daily", "count": 2})
        ends = [o["end"] for o in self.s.occurrences(daily["id"], "2026-03-07T00:00", "2026-03-10T00:00")]
        self.assertEqual(ends, ["2026-03-07T03:00-05:00", "2026-03-08T04:00-04:00"])

    def test_r5_reminders_count_elapsed_minutes(self):
        self.event(self.ny, "2026-03-07T03:30", rule={"freq": "daily"}, remind=[60])
        self.clock.advance(days=7, hours=1)                       # 2026-03-08T09:00Z
        due = self.s.reminders_due("2026-03-08T00:00")
        self.assertEqual([(d["start"], d["fire_at"], d["minutes"]) for d in due],
                         [("2026-03-08T03:30-04:00", "2026-03-08T01:30-05:00", 60)])

    def test_r5_reminder_window_and_zone(self):
        self.event(self.berlin, "2026-03-10T10:00", title="Planning", remind=[10, 60])
        self.clock.advance(days=9, minutes=50)                    # 2026-03-10T08:50Z
        due = self.s.reminders_due("2026-03-10T08:00Z")
        self.assertEqual(due, [{"event": "ev1", "title": "Planning", "start": "2026-03-10T10:00+01:00",
                                "minutes": 10, "fire_at": "2026-03-10T09:50+01:00"}])
        both = self.s.reminders_due("2026-03-10T07:59")           # no offset: UTC
        self.assertEqual([(d["minutes"], d["fire_at"]) for d in both],
                         [(60, "2026-03-10T09:00+01:00"), (10, "2026-03-10T09:50+01:00")])
        self.assertEqual(self.s.reminders_due("2026-03-10T08:50Z"), [])


class TestDays(Base):
    def test_r6_agenda_uses_the_users_day(self):
        self.event(self.utc, "2026-01-13T04:30", title="Late", attendees=["ann", "dee"])
        ann = self.s.agenda_for("ann", "2026-01-12")
        self.assertEqual([(i["title"], i["start"], i["end"]) for i in ann],
                         [("Late", "2026-01-12T23:30-05:00", "2026-01-13T00:00-05:00")])
        self.assertEqual(self.s.agenda_for("ann", "2026-01-13"), [])
        self.assertEqual(self.s.agenda_for("dee", "2026-01-12"), [])
        self.assertEqual(self.s.agenda_for("dee", "2026-01-13")[0]["start"], "2026-01-13T04:30+00:00")

    def test_r6_a_short_day_is_23_hours(self):
        for start in ("2026-03-08T00:30", "2026-03-08T23:30", "2026-03-09T00:00"):
            self.event(self.ny, start, title=start[5:], attendees=["ann"])
        self.assertEqual([i["title"] for i in self.s.agenda_for("ann", "2026-03-08")], ["03-08T00:30", "03-08T23:30"])
        self.assertEqual([i["title"] for i in self.s.agenda_for("ann", "2026-03-09")], ["03-09T00:00"])

    def test_r6_a_long_day_is_25_hours(self):
        for start in ("2026-11-01T00:30", "2026-11-01T23:30", "2026-11-02T00:00"):
            self.event(self.ny, start, title=start[5:], attendees=["ann"])
        self.assertEqual([i["title"] for i in self.s.agenda_for("ann", "2026-11-01")], ["11-01T00:30", "11-01T23:30"])
        self.assertEqual([i["title"] for i in self.s.agenda_for("ann", "2026-11-02")], ["11-02T00:00"])

    def test_r6_week(self):
        self.event(self.ny, "2026-03-04T09:00", attendees=["ann"])
        week = self.s.week_for("ann", "2026-03-02")
        self.assertEqual(list(week), [f"2026-03-0{d}" for d in range(2, 9)])
        self.assertEqual([len(v) for v in week.values()], [0, 0, 1, 0, 0, 0, 0])
        self.assertEqual(week["2026-03-04"][0]["start"], "2026-03-04T09:00-05:00")

    def test_r6_digest_is_in_local_time(self):
        self.event(self.utc, "2026-01-12T14:00", title="Standup", attendees=["ann", "ben", "cy", "dee"])
        self.assertEqual(self.s.digest("ann", "2026-01-12"), "Ann - Mon 12 Jan\n09:00-09:30 Standup")
        self.assertEqual(self.s.digest("ben", "2026-01-12"), "Ben - Mon 12 Jan\n15:00-15:30 Standup")
        self.assertEqual(self.s.digest("cy", "2026-01-12"), "Cy - Mon 12 Jan\n19:30-20:00 Standup")
        self.assertEqual(self.s.digest("dee", "2026-01-12"), "Dee - Mon 12 Jan\n14:00-14:30 Standup")

    def test_r6_digest_day_is_local(self):
        self.event(self.utc, "2026-01-12T20:00", title="Late", attendees=["cy"])
        self.assertEqual(self.s.digest("cy", "2026-01-13"), "Cy - Tue 13 Jan\n01:30-02:00 Late")
        self.assertEqual(self.s.digest("cy", "2026-01-12"), "Cy - Mon 12 Jan\nNo events.")


class TestWorkingHours(Base):
    def slots(self, users, day, duration, **kw):
        return [(s["start"], s["end"]) for s in self.s.free_slots(users, day, duration, **kw)]

    def test_r7_windows_in_different_zones(self):
        got = self.slots(["ann", "ben"], "2026-03-10", "1h")      # NY is on summer time, Berlin is not yet
        self.assertEqual([s for s, _ in got], [f"2026-03-10T{h}+00:00" for h in
                                               ("13:00", "13:30", "14:00", "14:30", "15:00")])
        self.assertEqual(got[-1][1], "2026-03-10T16:00+00:00")
        before = self.slots(["ann", "ben"], "2026-03-03", "1h")   # both on winter time
        self.assertEqual([s for s, _ in before], [f"2026-03-03T{h}+00:00" for h in ("14:00", "14:30", "15:00")])

    def test_r7_slots_can_be_shown_in_another_zone(self):
        got = self.slots(["ann", "ben"], "2026-03-10", "1h", tz="America/New_York")
        self.assertEqual(got[0], ("2026-03-10T09:00-04:00", "2026-03-10T10:00-04:00"))
        self.assertEqual(got[-1], ("2026-03-10T11:00-04:00", "2026-03-10T12:00-04:00"))
        self.assertEqual(self.slots(["ann"], "2026-03-10", "8h", tz="Asia/Kolkata"),
                         [("2026-03-10T18:30+05:30", "2026-03-11T02:30+05:30")])
        with self.assertRaises(InvalidZone):
            self.s.free_slots(["ann"], "2026-03-10", "1h", tz="Nowhere/Land")

    def test_r7_one_zone_across_a_clock_change(self):
        self.assertEqual(self.slots(["ann"], "2026-03-06", "8h"), [("2026-03-06T14:00+00:00", "2026-03-06T22:00+00:00")])
        self.assertEqual(self.slots(["ann"], "2026-03-09", "8h"), [("2026-03-09T13:00+00:00", "2026-03-09T21:00+00:00")])
        self.assertEqual(self.slots(["ann"], "2026-11-02", "8h"), [("2026-11-02T14:00+00:00", "2026-11-02T22:00+00:00")])

    def test_r7_busy_time_blocks_slots(self):
        self.event(self.utc, "2026-03-10T14:00", "1h", attendees=["ben"])
        got = self.slots(["ann", "ben"], "2026-03-10", "1h")
        self.assertEqual([s for s, _ in got], ["2026-03-10T13:00+00:00", "2026-03-10T15:00+00:00"])

    def test_r7_hours_are_local_to_the_user(self):
        self.s.add_user("kay", "Kay", hours={"mon": ["08:00", "12:00"]}, tz="Asia/Kolkata")
        got = self.slots(["kay"], "2026-03-09", "2h", tz="Asia/Kolkata")
        self.assertEqual(got[0], ("2026-03-09T08:00+05:30", "2026-03-09T10:00+05:30"))
        self.assertEqual((len(got), got[-1][0]), (5, "2026-03-09T10:00+05:30"))
        self.assertEqual(self.slots(["kay"], "2026-03-10", "1h"), [])
        self.assertEqual(self.slots(["ann", "kay"], "2026-03-09", "1h"), [])   # no shared time at all

    def test_r7_the_date_is_the_users_local_date(self):
        self.s.add_user("nit", "Nit", hours={"tue": ["00:00", "02:00"]}, tz="Asia/Kolkata")
        got = self.slots(["nit"], "2026-03-10", "1h")
        self.assertEqual(got, [("2026-03-09T18:30+00:00", "2026-03-09T19:30+00:00"),
                               ("2026-03-09T19:00+00:00", "2026-03-09T20:00+00:00"),
                               ("2026-03-09T19:30+00:00", "2026-03-09T20:30+00:00")])

    def test_r7_days_off(self):
        self.assertEqual(self.slots(["ann"], "2026-03-07", "1h"), [])
        self.assertEqual(self.slots(["ann", "ben"], "2026-03-08", "1h"), [])


class TestBooking(Base):
    def test_r8_conflicts_compare_instants(self):
        self.event(self.ny, "2026-03-10T09:00", "1h", attendees=["ann"])          # 13:00Z to 14:00Z
        with self.assertRaises(Conflict) as ctx:
            self.s.book(self.berlin, "Sync", "2026-03-10T14:00", "30m", ["ben", "ann"])
        self.assertEqual((ctx.exception.code, ctx.exception.param), ("conflict", "attendees"))
        self.assertIn("ann", ctx.exception.message)
        self.assertNotIn("ben", ctx.exception.message)
        with self.assertRaises(Conflict):
            self.s.book(self.utc, "Sync", "2026-03-10T13:30Z", "30m", ["ann"])
        ok = self.s.book(self.berlin, "Sync", "2026-03-10T09:00", "30m", ["ben", "ann"])   # 08:00Z
        self.assertEqual((ok["start"], ok["end"]), ("2026-03-10T09:00+01:00", "2026-03-10T09:30+01:00"))

    def test_r8_touching_events_do_not_conflict(self):
        self.event(self.ny, "2026-03-10T09:00", "1h", attendees=["ann"])
        self.assertEqual(self.s.book(self.berlin, "Next", "2026-03-10T15:00", "1h", ["ann"])["status"], "active")

    def test_r8_outside_hours_are_judged_locally(self):
        got = self.s.book(self.ny, "Late", "2026-03-10T11:30", "1h", ["ann", "ben"])      # Berlin 16:30-17:30
        self.assertEqual(got["outside_hours"], ["ben"])
        got = self.s.book(self.ny, "Early", "2026-03-10T08:00", "30m", ["ann", "ben"])    # Berlin 13:00
        self.assertEqual(got["outside_hours"], ["ann"])
        got = self.s.book(self.ny, "Edge", "2026-03-10T16:00", "1h", ["ann", "ben"])      # ends 17:00 in NY
        self.assertEqual(got["outside_hours"], ["ben"])
        got = self.s.book(self.ny, "Fine", "2026-03-10T10:00", "1h", ["ann", "ben"])
        self.assertEqual(got["outside_hours"], [])

    def test_r8_outside_hours_keep_the_given_order_and_weekends(self):
        got = self.s.book(self.ny, "Weekend", "2026-03-07T10:00", "1h", ["ben", "ann"])
        self.assertEqual(got["outside_hours"], ["ben", "ann"])

    def test_r8_local_date_of_the_start_decides_the_weekday(self):
        # Sunday 21:00Z is already Monday 02:30 in Kolkata, outside 09:00-17:00 there
        got = self.s.book(self.utc, "Odd", "2026-03-08T21:00Z", "1h", ["cy"])
        self.assertEqual(got["outside_hours"], ["cy"])
        got = self.s.book(self.utc, "Fine", "2026-03-09T05:00Z", "1h", ["cy"])           # Monday 10:30 in Kolkata
        self.assertEqual(got["outside_hours"], [])

    def test_r8_cancelled_events_do_not_block(self):
        ev = self.event(self.ny, "2026-03-10T09:00", "1h", attendees=["ann"])
        self.s.cancel_event(ev["id"])
        self.assertEqual(self.s.book(self.berlin, "Sync", "2026-03-10T14:00", "30m", ["ann"])["id"], "ev2")


class TestIcs(Base):
    def lines(self, cal):
        return self.s.export_ics(cal).split("\r\n")

    def test_r9_times_are_utc(self):
        self.event(self.ny, "2026-01-12T09:00", "45m", title="Winter")
        self.event(self.ny, "2026-07-06T09:00", title="Summer")
        self.event(self.kol, "2026-01-12T09:00")
        ny, kol = self.lines(self.ny), self.lines(self.kol)
        self.assertIn("DTSTAMP:20260301T080000Z", ny)
        self.assertIn("DTSTART:20260112T140000Z", ny)
        self.assertIn("DTEND:20260112T144500Z", ny)
        self.assertIn("DTSTART:20260706T130000Z", ny)
        self.assertIn("DTSTART:20260112T033000Z", kol)
        self.assertIn("DTEND:20260112T040000Z", kol)

    def test_r9_exdate_and_until_use_the_local_time_of_day(self):
        daily = self.event(self.ny, "2026-03-07T09:00", rule={"freq": "daily", "count": 5})
        self.s.skip_occurrence(daily["id"], "2026-03-09")
        self.s.skip_occurrence(daily["id"], "2026-03-07")
        self.event(self.ny, "2026-03-02T09:00", rule={"freq": "weekly", "weekdays": ["mon", "wed"],
                                                      "until": "2026-03-31"})
        lines = self.lines(self.ny)
        self.assertIn("DTSTART:20260307T140000Z", lines)
        self.assertIn("RRULE:FREQ=DAILY;INTERVAL=1;COUNT=5", lines)
        self.assertEqual([l for l in lines if l.startswith("EXDATE")],
                         ["EXDATE:20260307T140000Z", "EXDATE:20260309T130000Z"])
        self.assertIn("DTSTART:20260302T140000Z", lines)
        self.assertIn("RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE;UNTIL=20260331T130000Z", lines)

    def test_r9_nothing_is_floating(self):
        self.event(self.berlin, "2026-10-26T09:00", rule={"freq": "daily", "until": "2026-10-30"})
        self.s.skip_occurrence("ev1", "2026-10-27")
        for line in self.lines(self.berlin):
            if line.split(":")[0] in ("DTSTAMP", "DTSTART", "DTEND", "EXDATE"):
                self.assertTrue(line.endswith("Z"), line)
        self.assertIn("RRULE:FREQ=DAILY;INTERVAL=1;UNTIL=20261030T080000Z", self.lines(self.berlin))


class TestSnapshot(Base):
    def test_r10_dump_stores_utc_and_zones(self):
        self.event(self.ny, "2026-01-12T09:00", rule={"freq": "daily", "count": 2})
        data = self.s.dump()
        self.assertEqual({u["id"]: u["tz"] for u in data["users"]},
                         {"ann": "America/New_York", "ben": "Europe/Berlin", "cy": "Asia/Kolkata", "dee": "UTC"})
        self.assertEqual([c["tz"] for c in data["calendars"]],
                         ["America/New_York", "Europe/Berlin", "Asia/Kolkata", "UTC"])
        self.assertEqual(data["events"][0]["start"], "2026-01-12T14:00Z")

    def test_r10_round_trip_through_json(self):
        ev = self.event(self.ny, "2026-03-06T09:00", rule={"freq": "daily", "count": 5}, attendees=["ann"],
                        remind=[30])
        self.s.skip_occurrence(ev["id"], "2026-03-10")
        self.event(self.kol, "2026-01-12T09:00", title="Kolkata")
        copy = Scheduler.load(json.loads(json.dumps(self.s.dump())), clock=self.clock)
        for event_id in ("ev1", "ev2"):
            self.assertEqual(copy.get_event(event_id), self.s.get_event(event_id))
        self.assertEqual(copy.occurrences("ev1", "2026-03-06T00:00", "2026-03-12T00:00"),
                         self.s.occurrences("ev1", "2026-03-06T00:00", "2026-03-12T00:00"))
        self.assertEqual(copy.occurrences("ev1", "2026-03-08T00:00", "2026-03-09T00:00")[0]["start"],
                         "2026-03-08T09:00-04:00")
        self.assertEqual(copy.free_slots(["ann", "ben"], "2026-03-10", "1h"),
                         self.s.free_slots(["ann", "ben"], "2026-03-10", "1h"))
        self.assertEqual(copy.add_user("new", "New", tz="UTC")["tz"], "UTC")

    def test_r10_older_dump_is_all_utc(self):
        old = {"version": 1,
               "users": [{"id": "ann", "name": "Ann", "hours": {"mon": ["09:00", "17:00"]}}],
               "calendars": [{"id": "cal1", "name": "Team"}],
               "events": [{"id": "ev1", "calendar": "cal1", "title": "Standup", "start": "2026-03-02T09:00",
                           "duration": 30, "attendees": ["ann"], "rule": {"freq": "daily", "interval": 1,
                                                                          "count": 2, "until": None,
                                                                          "weekdays": []},
                           "skips": [], "status": "active", "remind": [10]}]}
        copy = Scheduler.load(old, clock=self.clock)
        self.assertEqual(copy.get_event("ev1")["start"], "2026-03-02T09:00+00:00")
        self.assertEqual(copy.agenda_for("ann", "2026-03-03")[0]["start"], "2026-03-03T09:00+00:00")
        self.assertEqual(copy.dump()["events"][0]["start"], "2026-03-02T09:00Z")


if __name__ == "__main__":
    unittest.main()
