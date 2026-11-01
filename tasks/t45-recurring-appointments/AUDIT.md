# t45-recurring-appointments: where each hidden-test rule comes from

Category `clarify-first`. The prompt asks for repeating appointments on a clinic calendar and leaves five
decisions open. They are answered only by `answers.json` (outside `repo/`, served by the `ask_user` tool).
Everything else is shown by the prompt or the repo. Agents never see this file.

| Test (class) | Rule | Source |
|---|---|---|
| `test_operations_are_registered` | three operations registered by name; module imported in `ops/__init__.py` | prompt (names); `ops/__init__.py` comment; `ops/registry.py` |
| `test_series_view` | id `series_0001` from `ids.new("series")`; `patient`, `repeat`, `status` `active`; created_at = updated_at = now, version 1; `appointments` in date order, ids `appointment_0001...` | prompt (fields, date order); `ids.py`; `views.stamp`; `ops/patients.py`; `ops/appointments.py` (prefix `appointment`) |
| `test_the_appointments_are_real` | each occurrence is a booked appointment of the patient, same length, version 1, created now, listed by `appointment.list` | prompt ("books them", "as for `appointment.book`"); `appointment.book` |
| `test_create_event` | one event `series.created` with the series view; the appointments change silently | `service.call` docstring |
| `test_unknown_and_missing_arguments`, `test_the_first_slot_must_be_in_the_future` | NotFound on `patient`; InvalidRequest on `start`, `minutes`; a start that is not after now is refused | `validate.appointment_span`, `store.get_patient`; prompt ("all as for `appointment.book`") |
| `test_failures_change_nothing` and "refusals change nothing" asserts | no event, no appointment, no id taken on failure | `service.call` docstring |
| `test_retrieve` | reads emit nothing, NotFound / InvalidRequest on `series` | prompt; `appointment.retrieve`; docstring |
| `TestMonthEnd` (6) | a monthly series keeps the first day of month; short months use their last day; later months return to the original day; leap years; year change; time unchanged; no month skipped | answers.json `month_end` |
| `TestClashes` (8) | clashing occurrences are skipped, `skipped` lists them (empty when none), `count` includes skipped ones, touching slots do not clash, cancelled appointments do not clash, a clash on the first occurrence refuses everything (Conflict on `start`) | answers.json `clashes`; overlap and cancelled rule: `Store.clashes` docstring |
| `TestCount` (5) | `count` is a whole number 2 to 12 (InvalidRequest on `count`); `repeat` must be `weekly` or `monthly` (InvalidRequest on `repeat`) | answers.json `count` (the `repeat` part is also in the prompt) |
| `TestCancel` (9) | cancel the occurrences starting strictly after now; started and past ones stay booked; earlier-cancelled ones untouched; series `cancelled`, `appointments` unchanged; version 2 for each changed record; one event; Conflict on `series` when repeated | answers.json `cancel_scope`; docstring (bump, one event) |
| `TestOneSeries` (3) | one active series per patient, Conflict on `patient`; free after cancelling; other patients unaffected | answers.json `one_series` |
| `TestRegression` | existing behaviour stays | `tests/test_clinic.py` |

## Decisions, plausible guesses, chance a pure guess passes

| Decision | Answer | Plausible guesses | Tests that fail on a wrong guess | P(guess right) |
|---|---|---|---|---|
| month_end | keep the original day; short months use their last day; later months return to the original day | skip the month; roll into the next month; stay on the clamped day afterwards (28th) | 5 | clamp only for that month about 25%; back to the original day about 10% overall |
| clashes | skip clashing occurrences, list them as `skipped`; refuse only when the first clashes | refuse the whole series (also likely); skip silently with no `skipped` field | 8 | skip-and-report with the first-occurrence exception about 8% |
| count | 2 to 12 inclusive | no limit; 1 to 12; 1 to 52; 2 to 10 | 3 | no limit 40%; exactly 2 to 12 about 4% |
| cancel_scope | not-yet-started occurrences only (strict), the series closes | cancel all; leave booked ones alone; start inclusive | 4 | cancel all 50%; the strict future boundary about 20% |
| one_series | one active series per patient | several allowed | 3 | allow several 65% |

A guess passes only if every decision is right: well under 1%.

What makes it hard: a series looks like a loop around `appointment.book`. The decisions are the calendar
edge cases (what a 31st means in February, what to do when a slot is taken, what a cancel leaves behind),
and the clash decision changes the series view itself (`skipped`).

## Keyword self-check

The server answers with every entry that has at least one keyword hit, so each keyword must point at its
own decision. Generated with `ate.askuser.server.match_answer` over `answers.json`: for each phrasing, the
ids that match (want exactly the decision asked about).

| Question | Decision asked | ids matched |
|---|---|---|
| What should a monthly series starting on the 31st do in February? | month_end | month_end |
| Should short months be skipped for a monthly appointment? | month_end | month_end |
| Which day of the month do later occurrences use? | month_end | month_end |
| What if one of the occurrences clashes with another appointment? | clashes | clashes |
| Should the whole series fail if the doctor is busy on one date? | clashes | clashes |
| Do overlapping slots get skipped? | clashes | clashes |
| How many occurrences can a series have at most? | count | count |
| What is the minimum count? | count | count |
| Is a count of 1 valid? | count | count |
| What does cancelling a series do to appointments that already happened? | cancel_scope | cancel_scope |
| Should series.cancel touch future appointments only? | cancel_scope | cancel_scope |
| What happens to the rest of the series when it is cancelled? | cancel_scope | cancel_scope |
| Can a patient have more than one series? | one_series | one_series |
| Can a patient create a second series while one is running? | one_series | one_series |
| Is there a limit of one series per patient? | one_series | one_series |
| What should the series id look like? | (none: not a decision) | none |
| Which event is emitted when a series is created? | (none: not a decision) | none |
| Should weekly mean every seven days? | (none: not a decision) | none |
| What does retrieve return? | (none: not a decision) | none |
