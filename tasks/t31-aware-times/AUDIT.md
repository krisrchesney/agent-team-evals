# t31-aware-times: where each hidden-test rule is shown

Category `cross-module`: the prompt lists ten numbered requirements, and the hidden tests (named
`test_r<N>_...`) hit every module that holds or compares a time. Every rule is in the prompt; the
starting code shows where each one has to be applied. This file is outside `repo/`, so agents never
see it.

| Test(s) | Rule | Shown by |
|---|---|---|
| `test_r1_zones_in_results`, `_invalid_zone`, `_clocks_are_aware` | users and calendars carry `tz`, `InvalidZone`, aware clocks | prompt 1; `users.py`, `calendars.py`, `clock.py` |
| `test_r2_*` (6 tests) | offset/Z strings, naive strings and datetimes read in the calendar's zone, bad input, `move_event`, `occurrences` windows | prompt 2; `timeparse.parse_dt`, `events.py`, `service.py` |
| `test_r3_results_are_in_the_calendar_zone`, `test_reg_utc_defaults` | output format with offset, per zone | prompt 3; `timeparse.fmt_dt` and every caller |
| `test_r4_daily_keeps_local_time_over_spring_forward`, `_weekly_..._fall_back_in_berlin`, `_monthly_clamps_and_follows_the_clock` | a repeat keeps its local time of day | prompt 4; `recurrence.expand` |
| `test_r4_missing_local_time_moves_forward`, `_repeated_local_time_is_the_first` | gap and fold rules | prompt 4 (rules written out; `zoneinfo` does this by default) |
| `test_r4_until_and_skip_are_local_dates`, `_weekdays_are_local` | rule dates, skips and weekdays are local | prompt 4; `events.parse_rule`, `recurrence.rule_dates` |
| `test_r4_lengths_are_elapsed_time` | end = start + duration in elapsed time, also across a clock change | prompt 4; `recurrence.expand` |
| `test_r5_*` | reminders count elapsed minutes, window ends, naive `since` is UTC, output in the event zone | prompt 5 and 2; `reminders.py` |
| `test_r6_*` (6 tests) | user-local days (23 and 25 hours), week keys, digest in local time and by local day | prompt 6; `agenda.py` |
| `test_r7_*` (7 tests) | windows from local hours, zone-dependent overlap (NY summer time vs Berlin winter time), `tz` for output, local date of `day`, day off | prompt 7 and 3; `availability.py` |
| `test_r8_*` (6 tests) | conflicts by instant, `outside_hours` judged locally, order, weekday of the local start date, cancelled events | prompt 8; `booking.py`, `availability.within_hours` |
| `test_r9_*` | ICS times in UTC, `EXDATE` and `UNTIL` at the local time of day | prompt 9; `ics.py` |
| `test_r10_*` | dump stores UTC and `tz`, round trip through JSON, older dumps read as UTC | prompt 10; `snapshot.py` |

The tests use the dates of the 2026 clock changes: New York 8 March (forward) and 1 November (back),
Berlin 29 March and 25 October. Between 8 and 29 March New York is on summer time and Berlin is not,
which is why the cross-zone overlap changes there.

What makes it hard: the change is spread over twelve modules and a mistake in any one fails a few
tests. The classic traps are all present: doing arithmetic on `ZoneInfo`-aware datetimes (wall-clock,
not elapsed), taking the date or weekday of a UTC instant instead of the local one, assuming every
day has 24 hours, and forgetting that `until`, skips and EXDATE are local dates. Nothing is hidden:
every rule is stated in the prompt.
