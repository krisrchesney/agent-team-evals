`sched` holds every time as a naive wall-clock datetime. That only works while the whole team sits in
one office and the clocks never change. Make the library timezone-aware throughout. Use only the
Python standard library (`zoneinfo` is fine). Existing setups, which have no zones, must keep working
by treating everything as UTC.

1. **Zones.** `add_user(user_id, name, hours=None, tz="UTC")` and `create_calendar(name, tz="UTC")`
   take an IANA zone name, and the dicts they return have `tz`. An unknown zone raises `InvalidZone`
   (code `invalid_zone`, `param="tz"`). A user's working `hours` are local times in the user's zone;
   an event lives in its calendar's zone. `SystemClock.now()` and `FixedClock.now()` return aware UTC
   datetimes (a naive `start` given to `FixedClock` is read as UTC).
2. **Input.** A time string may end in `Z` or an offset like `+05:30` and then means that instant. A
   string without an offset, or a naive `datetime`, is a local time in the zone of the event's
   calendar (`reminders_due` has no calendar: there it is UTC). An aware `datetime` means its instant.
   This covers `create_event`, `move_event`, `occurrences`, `book` and `reminders_due`. Inside the
   library, hold and compare instants, not wall-clock times.
3. **Output.** Times in results are ISO-8601 with the offset, to the minute, in the zone that applies:
   event views, `occurrences` and reminders in the event's calendar zone (`2026-03-08T09:00-04:00`;
   UTC is `+00:00`), `agenda_for` and `week_for` in the user's zone, and `free_slots` in the zone
   named by a new `tz` argument (default `"UTC"`). The visible tests compare the old naive strings:
   update them.
4. **Repeats.** A repeating event keeps its local time of day in its calendar's zone when the clocks
   change. The dates in a rule (`until`) and in `skip_occurrence` are local dates in that zone, and so
   are the weekdays of a weekly rule. A local time that does not exist on a date (the clocks jump
   forward) moves forward by the length of the gap; one that happens twice (they go back) means the
   first time. Lengths are elapsed time: an occurrence ends `duration` after it starts.
5. **Reminders.** `remind=[60]` means 60 minutes of elapsed time before the start, not 60 minutes on
   the wall clock.
6. **Days.** `agenda_for`, `week_for` and `digest` use the user's own local day, which can be 23 or 25
   hours long. A digest line (`HH:MM-HH:MM Title`) is in the user's local time.
7. **Working hours.** A user's working window on `day` is their hours for the weekday of the date
   `day` in the user's own zone. `free_slots` works on the intersection of those windows as before
   (first candidate where the shared window starts, then every `step` minutes, nobody busy).
8. **Booking.** `book` finds conflicts by comparing instants. `outside_hours` lists the attendees (in
   the order given) for whom the meeting is not wholly inside the working hours of the local day on
   which it starts for them.
9. **iCalendar.** Every time (`DTSTAMP`, `DTSTART`, `DTEND`, `EXDATE`, `UNTIL`) is written in UTC like
   `20260308T140000Z`. `EXDATE` is the skipped local date at the event's local time of day, and
   `UNTIL` is the `until` date at the event's local time of day.
10. **Save and load.** `dump()` writes event starts as UTC ending in `Z` (`2026-03-08T14:00Z`) and a
    `tz` for every user and calendar. `load()` restores them and still reads older dumps (no `tz`
    keys, starts without a `Z`: all UTC).
