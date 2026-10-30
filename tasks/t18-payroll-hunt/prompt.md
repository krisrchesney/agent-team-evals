`paykit` turns timesheets into pay. A small company runs it every week and reports that some
paychecks and report lines come out wrong, in ways nobody has pinned down. Fix the library so that
it meets the spec below, and add the CSV output described at the end. The spec is written as prose;
the numbered items (R1, R2, ...) are the individual requirements, and all of them apply.

**Shifts.** A shift is `Shift(employee_id, day, start, end, break_min=0)`. The `day` is a real
calendar date written `YYYY-MM-DD`, and `start` and `end` are 24-hour clock times written `HH:MM`
with two digits each, from `00:00` to `23:59`; anything else, including values that are not
strings, raises `ValueError` (R1). `Shift.day` is a `datetime.date`. When `end` is earlier than
`start` the shift ends on the next day; `Shift.duration` is the number of minutes between the two
times on that basis, and a shift whose `end` equals its `start` raises `ValueError` (R2). The
`break_min` must be an `int` (a `bool` does not count) that is at least 0 and shorter than the
shift's duration, otherwise `ValueError` (R3). The unpaid break that is deducted is `break_min`,
except that a shift longer than 360 minutes (strictly longer: exactly 360 is not) which recorded
less than 30 minutes of break has 30 minutes deducted instead (R4). `Shift.paid_minutes` is the
duration minus that unpaid break, rounded to the nearest multiple of 15 minutes: a remainder of 7
or less rounds down and a remainder of 8 or more rounds up (R5).

**Employees and rates.** An employee is `Employee(emp_id, name, rates)` where `rates` is a list of
`(effective_day, cents_per_hour)` pairs. `emp_id` must be a non-empty string and `name` a string
that is not blank; `rates` must not be empty; every rate must be an `int` (not a `bool`) greater
than 0 and every effective day a valid `YYYY-MM-DD` text; otherwise `ValueError` (R6).
`Employee.rate_on(day)` takes a `YYYY-MM-DD` text and returns the rate with the latest effective
day that is not after `day`; a rate takes effect on its effective day itself. A day before the
first effective day raises `ValueError`. The pairs may be given in any order (R7). No function in
the library modifies the lists or objects it is given: not the rates list, not the lists of
employees or shifts passed to the payroll functions (R8).

**Weeks and overtime.** Pay weeks run from Monday to Sunday, including a week that spans two
calendar years, and a shift belongs to the week of the day it starts on, so an overnight shift
that starts on a Sunday counts in that Sunday's week (R9). For one employee in one pay week the
shifts are taken in time order, by day and then by start time. The first 2400 paid minutes (40
hours) of the week are regular and every paid minute after that is overtime; a shift that crosses
the limit is split between regular and overtime minutes (R10). Each shift's regular and overtime
minutes are paid at the employee's rate on the day of that shift, even if the rate changed during
the week (R11). Regular minutes pay `rate * minutes / 60` cents and overtime minutes pay one and a
half times that, `rate * minutes * 3 / 120` cents, each rounded to a whole cent with halves
rounding up (0.5 becomes 1). The regular part and the overtime part are rounded separately for each
shift, and the rounded amounts are added up (R12).

**Pay rows.** `weekly_breakdown(employees, shifts)` returns a list of `WeekRow` objects, one for
each employee and pay week that has shifts. A `WeekRow` has the attributes `employee_id`, `name`,
`week_start` (the Monday of the week, a `datetime.date`), `regular_minutes`, `overtime_minutes` and
`gross_cents`. The rows are ordered by employee name ignoring upper and lower case, then by employee
id, then by `week_start`. A shift whose employee id is not in `employees` raises `ValueError` with
the message `unknown employee 'x'` (the repr of the id); employees without shifts get no rows
(R13). `compute_payroll(employees, shifts)` returns one `PayRow` per employee that has shifts,
with the attributes `employee_id`, `name`, `regular_minutes`, `overtime_minutes` and `gross_cents`,
which are the sums over all that employee's weeks. The rows are ordered by name ignoring case, then
by id, and with no shifts the list is empty (R14).

**Loading shifts.** `load_shifts(text)` reads CSV text and returns a list of `Shift` objects in file
order. The first line that is not blank is the header and must be exactly
`employee_id,day,start,end,break_min`. Blank lines (empty or only spaces) are ignored anywhere,
fields are stripped of surrounding spaces, and every row has exactly 4 or 5 fields; a missing or
empty `break_min` means 0 (R15). Every error is a `ValueError` whose message starts with `line N: `,
where N is the physical line number in the text, counting from 1 and counting blank lines. This
covers a wrong header, a wrong number of fields, a `break_min` that is not an integer, and any
problem that `Shift` itself rejects (R16). `find_overlaps(shifts)` returns a list of pairs `(a, b)`
of shifts of the same employee that share some time. An overnight shift runs into the next day, and
a shift that ends exactly when another starts does not overlap it. `a` comes before `b` in the
input list, and the pairs are ordered by the position of `a`, then the position of `b` (R17).

**Formatting.** In `paykit.money`, `format_cents(cents)` gives a dollar sign, thousands separators
and exactly two decimals, so 123456 is `$1,234.56` and 0 is `$0.00`; a negative amount puts the
minus sign before the dollar sign, `-$5.00` (R18). `format_hours(minutes)` gives the minutes as
hours rounded to exactly two decimals and with no thousands separator: 450 is `7.50`, 0 is `0.00`,
100 is `1.67` and 75000 is `1250.00` (R19).

**The text report.** In `paykit.report`, `render_text(rows)` takes a list of `PayRow` and returns
text with these lines, in order: the title `Payroll report`; a line of `=` as long as the title; a
header line; a rule line; one line per row; the rule line again; a `TOTAL` line; and a count line.
Each line ends with `"\n"`, and there are no trailing spaces (R20). The columns are `Employee`
(left-aligned, 12 wide), `Reg hrs` (right-aligned, 7 wide), `OT hrs` (right-aligned, 6 wide) and
`Gross` (right-aligned, 12 wide), separated by two spaces; the header uses the same alignment, and
the rule line is `-` repeated to each column's width with two spaces between. Regular and overtime
hours use `format_hours` and gross uses `format_cents`. A name longer than 12 characters is
replaced by its first 9 characters followed by `...`; a name of exactly 12 characters is written in
full (R21). The `TOTAL` row has the same columns and holds the sums over all rows. The count line is
`1 employee` for one row and `N employees` for any other number (R22). With no rows the report is
just the title, its `=` line and the line `No shifts.` (R23). `render_weekly(week_rows)` takes a list
of `WeekRow` and returns the title `Weekly breakdown`, a line of `=` as long as the title, a header
line, a rule line and one line per row, each ending in `"\n"`, with no total and no count line. Its
columns are `Employee` (left, 12 wide), `Week of` (left, 10 wide, the `week_start` as
`YYYY-MM-DD`), `Reg hrs` (right, 7), `OT hrs` (right, 6) and `Gross` (right, 12), separated by two
spaces, and names are shortened as in R21. With no rows it is the title, its `=` line and `No
shifts.` (R24).

**CSV output (new).** Add `render(rows, fmt="text")` to `paykit.report`: `"text"` returns exactly
what `render_text` returns, `"csv"` returns the CSV below, and any other value raises `ValueError`
with the message `unknown format` followed by the repr of the value (`unknown format 'xml'`). The
text report must come out exactly as before, for every input (R25). The CSV starts with the header
line `employee_id,name,regular_hours,overtime_hours,gross`, then one line per row in the same order
as the text report, with the hours written like `format_hours` and the gross written as dollars and
cents with two decimals and no currency symbol and no thousands separator (`1234.56`). Names are
written in full, never shortened. An id or name containing a comma, a double quote, a carriage
return or a line feed is wrapped in double quotes with each inner double quote doubled. Lines end
with `"\n"`, including the last, and with no rows the CSV is just the header line (R26).

**Command line.** `paykit.cli.main(argv)` takes the arguments after the program name:
a shifts CSV file, an employees JSON file, and optionally `--format text` or `--format csv`
(the option may come before, between or after the two paths; the default is `text`). The employees
file is a JSON list of objects such as `{"id": "e1", "name": "Ann", "rates": [["2024-01-01", 2000]]}`.
`main` writes the report to standard output and returns 0. For every problem (the wrong number of
arguments, a file that cannot be read, malformed JSON or shifts, an unknown employee, an unknown
format) it writes `error: ` and the message to standard error, writes nothing to standard output,
and returns 2; the message for wrong arguments is `usage: paykit SHIFTS.csv EMPLOYEES.json [--format
text|csv]`. For each pair found by `find_overlaps` it first writes the line `warning: overlapping
shifts for <employee id> on <day of the first shift, YYYY-MM-DD>` to standard error, and carries on
as usual (R27).

Keep the public names and signatures as they are, and use only the Python standard library.
Existing tests are in `tests/`.
