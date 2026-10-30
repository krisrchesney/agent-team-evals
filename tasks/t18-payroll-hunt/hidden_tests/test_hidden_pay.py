"""Hidden grader for t18, part 2: weeks, overtime, pay rows, loading and overlaps (R9 to R17).
Tests are named after the requirement they check; the ones marked BUG isolate one planted bug."""
import datetime
import unittest

from paykit import compute_payroll, find_overlaps, load_shifts, weekly_breakdown

from ._common import HEADER, add_days, day, emp, sh, weekdays


class HiddenPay(unittest.TestCase):
    # ---- R9 weeks ---------------------------------------------------------------------------------
    def test_R9_week_runs_monday_to_sunday(self):
        shifts = [sh(add_days("2024-03-04", n), "09:00", "12:00") for n in range(7)]
        shifts.append(sh("2024-03-11", "09:00", "12:00"))
        rows = weekly_breakdown([emp()], shifts)
        self.assertEqual([r.week_start for r in rows], [day("2024-03-04"), day("2024-03-11")])
        self.assertEqual([r.regular_minutes for r in rows], [7 * 180, 180])

    def test_R9_week_spanning_new_year_is_one_week_BUG(self):
        shifts = weekdays("2024-12-30") + [sh("2025-01-04", "08:00", "12:00")]
        rows = weekly_breakdown([emp()], shifts)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].week_start, day("2024-12-30"))
        self.assertEqual((rows[0].regular_minutes, rows[0].overtime_minutes), (2400, 240))
        self.assertEqual(rows[0].gross_cents, 80000 + 12000)
        (total,) = compute_payroll([emp()], shifts)
        self.assertEqual(total.gross_cents, 92000)

    def test_R9_same_week_number_in_different_years_is_a_different_week(self):
        shifts = [sh("2024-03-04", "09:00", "12:00"), sh("2025-03-03", "09:00", "12:00")]
        rows = weekly_breakdown([emp()], shifts)
        self.assertEqual([r.week_start for r in rows], [day("2024-03-04"), day("2025-03-03")])

    def test_R9_overnight_shift_on_sunday_belongs_to_its_start_week(self):
        shifts = [sh("2024-03-10", "22:00", "06:00"), sh("2024-03-11", "09:00", "12:00")]
        rows = weekly_breakdown([emp()], shifts)
        self.assertEqual([(r.week_start, r.regular_minutes) for r in rows],
                         [(day("2024-03-04"), 450), (day("2024-03-11"), 180)])

    # ---- R10 overtime -----------------------------------------------------------------------------------
    def test_R10_overtime_after_forty_paid_hours(self):
        shifts = weekdays("2024-03-04") + [sh("2024-03-09", "08:00", "12:00")]
        (row,) = weekly_breakdown([emp()], shifts)
        self.assertEqual((row.regular_minutes, row.overtime_minutes), (2400, 240))

    def test_R10_exactly_forty_hours_has_no_overtime(self):
        (row,) = weekly_breakdown([emp()], weekdays("2024-03-04"))
        self.assertEqual((row.regular_minutes, row.overtime_minutes), (2400, 0))

    def test_R10_shift_that_crosses_the_limit_is_split(self):
        shifts = weekdays("2024-03-04")[:4] + [sh("2024-03-08", "08:00", "18:00", 60)]
        (row,) = weekly_breakdown([emp()], shifts)
        self.assertEqual((row.regular_minutes, row.overtime_minutes), (2400, 60))

    def test_R10_input_order_does_not_matter(self):
        shifts = weekdays("2024-03-04")[:4] + [sh("2024-03-08", "08:00", "18:00", 60)]
        (row,) = weekly_breakdown([emp()], list(reversed(shifts)))
        self.assertEqual((row.regular_minutes, row.overtime_minutes, row.gross_cents),
                         (2400, 60, 2400 * 2000 // 60 + 2000 * 60 * 3 // 120))

    def test_R10_the_limit_is_per_employee_and_per_week(self):
        employees = [emp("e1", "Ann"), emp("e2", "Bob")]
        shifts = (weekdays("2024-03-04") + weekdays("2024-03-11")
                  + weekdays("2024-03-04", emp_id="e2"))
        rows = weekly_breakdown(employees, shifts)
        self.assertEqual([(r.employee_id, r.week_start.isoformat(), r.regular_minutes,
                           r.overtime_minutes) for r in rows],
                         [("e1", "2024-03-04", 2400, 0), ("e1", "2024-03-11", 2400, 0),
                          ("e2", "2024-03-04", 2400, 0)])

    def test_R10_overtime_goes_to_the_latest_shifts_in_time_order_BUG(self):
        e = emp(rates=[("2024-01-01", 2000), ("2024-03-09", 3000)])
        # Saturday starts earlier in the day than the weekdays but comes later in the week.
        shifts = weekdays("2024-03-04") + [sh("2024-03-09", "06:00", "10:00")]
        (row,) = weekly_breakdown([e], shifts)
        self.assertEqual((row.regular_minutes, row.overtime_minutes), (2400, 240))
        self.assertEqual(row.gross_cents, 5 * 16000 + 18000)  # Saturday is all overtime at 3000

    # ---- R11 rates by day ------------------------------------------------------------------------------------
    def test_R11_each_shift_uses_the_rate_of_its_own_day(self):
        e = emp(rates=[("2024-01-01", 2000), ("2024-03-07", 3000)])
        shifts = [sh("2024-03-06", "08:00", "17:00", 60), sh("2024-03-07", "08:00", "17:00", 60)]
        (row,) = compute_payroll([e], shifts)
        self.assertEqual(row.gross_cents, 16000 + 24000)

    def test_R11_overtime_uses_the_rate_of_the_shift_it_belongs_to(self):
        e = emp(rates=[("2024-01-01", 2000), ("2024-03-08", 3000)])
        shifts = weekdays("2024-03-04")[:4] + [sh("2024-03-08", "08:00", "18:00", 60)]
        (row,) = compute_payroll([e], shifts)
        # Mon-Thu 4 x 8 h at 2000; Friday: 8 h regular at 3000 and 1 h overtime at 4500
        self.assertEqual(row.gross_cents, 64000 + 24000 + 4500)

    # ---- R12 pay formulas --------------------------------------------------------------------------------------
    def test_R12_regular_pay_formula(self):
        e = emp(rates=[("2024-01-01", 1999)])
        (a,) = compute_payroll([e], [sh("2024-03-04", "09:00", "09:45")])
        (b,) = compute_payroll([e], [sh("2024-03-04", "09:00", "09:15")])
        self.assertEqual((a.gross_cents, b.gross_cents), (1499, 500))  # 1499.25, 499.75

    def test_R12_overtime_pay_formula(self):
        e = emp(rates=[("2024-01-01", 1999)])
        shifts = weekdays("2024-03-04") + [sh("2024-03-09", "08:00", "08:45")]
        (row,) = compute_payroll([e], shifts)
        self.assertEqual(row.overtime_minutes, 45)
        self.assertEqual(row.gross_cents, 5 * 15992 + 2249)  # 2248.875 rounds up

    def test_R12_halves_round_up_BUG(self):
        (a,) = compute_payroll([emp(rates=[("2024-01-01", 1005)])],
                               [sh("2024-03-04", "09:00", "09:30")])
        self.assertEqual(a.gross_cents, 503)  # 502.5
        e = emp(rates=[("2024-01-01", 1004)])
        (b,) = compute_payroll([e], weekdays("2024-03-04") + [sh("2024-03-09", "08:00", "08:15")])
        self.assertEqual(b.gross_cents, 5 * 8032 + 377)  # overtime is 376.5

    def test_R12_each_shift_is_rounded_on_its_own(self):
        e = emp(rates=[("2024-01-01", 1001)])
        shifts = [sh("2024-03-04", "09:00", "09:15"), sh("2024-03-05", "09:00", "09:15")]
        (row,) = compute_payroll([e], shifts)
        self.assertEqual(row.gross_cents, 500)  # 250.25 twice; 30 minutes in one go would be 501

    # ---- R13 weekly rows ------------------------------------------------------------------------------------------
    def test_R13_rows_are_ordered_by_name_ignoring_case_then_id_then_week(self):
        employees = [emp("e1", "zed"), emp("e2", "Bob"), emp("e3", "adam")]
        shifts = [sh("2024-03-04", "09:00", "12:00", emp_id=i) for i in ("e1", "e2", "e3")]
        shifts.append(sh("2024-03-11", "09:00", "12:00", emp_id="e3"))
        shifts.append(sh("2024-03-04", "13:00", "14:00", emp_id="e3"))
        rows = weekly_breakdown(employees, shifts)
        self.assertEqual([(r.name, r.week_start.isoformat()) for r in rows],
                         [("adam", "2024-03-04"), ("adam", "2024-03-11"),
                          ("Bob", "2024-03-04"), ("zed", "2024-03-04")])

    def test_R13_same_name_is_ordered_by_id(self):
        employees = [emp("b2", "Sam"), emp("a1", "Sam")]
        shifts = [sh("2024-03-04", "09:00", "12:00", emp_id="b2"),
                  sh("2024-03-04", "09:00", "12:00", emp_id="a1")]
        self.assertEqual([r.employee_id for r in weekly_breakdown(employees, shifts)],
                         ["a1", "b2"])

    def test_R13_row_attributes(self):
        (row,) = weekly_breakdown([emp("e7", "Bob")], [sh("2024-03-06", "09:00", "12:00", emp_id="e7")])
        self.assertEqual(row.employee_id, "e7")
        self.assertEqual(row.name, "Bob")
        self.assertIsInstance(row.week_start, datetime.date)
        self.assertEqual((row.regular_minutes, row.overtime_minutes, row.gross_cents),
                         (180, 0, 6000))

    def test_R13_unknown_employee_is_an_error(self):
        shifts = [sh("2024-03-04", "09:00", "12:00"), sh("2024-03-04", "09:00", "12:00", emp_id="zz")]
        for func in (weekly_breakdown, compute_payroll):
            with self.subTest(func=func.__name__):
                with self.assertRaises(ValueError) as cm:
                    func([emp()], shifts)
                self.assertEqual(str(cm.exception), "unknown employee 'zz'")

    def test_R13_employees_without_shifts_have_no_rows(self):
        employees = [emp("e1", "Ann"), emp("e2", "Bob")]
        rows = weekly_breakdown(employees, [sh("2024-03-04", "09:00", "12:00", emp_id="e2")])
        self.assertEqual([r.employee_id for r in rows], ["e2"])

    # ---- R14 pay rows ----------------------------------------------------------------------------------------------
    def test_R14_totals_are_sums_over_the_weeks(self):
        shifts = [sh("2024-03-04", "09:00", "12:00"), sh("2024-03-12", "09:00", "11:00")]
        (row,) = compute_payroll([emp("e1", "Ann Lee")], shifts)
        self.assertEqual((row.employee_id, row.name), ("e1", "Ann Lee"))
        self.assertEqual((row.regular_minutes, row.overtime_minutes, row.gross_cents),
                         (300, 0, 10000))

    def test_R14_totals_include_overtime_from_each_week(self):
        shifts = (weekdays("2024-03-04") + [sh("2024-03-09", "08:00", "10:00")]
                  + weekdays("2024-03-11") + [sh("2024-03-16", "08:00", "09:00")])
        (row,) = compute_payroll([emp()], shifts)
        self.assertEqual((row.regular_minutes, row.overtime_minutes), (4800, 180))

    def test_R14_rows_are_ordered_by_name_then_id(self):
        employees = [emp("e1", "zed"), emp("e2", "Bob"), emp("e3", "adam"), emp("a0", "bob")]
        shifts = [sh("2024-03-04", "09:00", "12:00", emp_id=i) for i in ("e1", "e2", "e3", "a0")]
        self.assertEqual([r.employee_id for r in compute_payroll(employees, shifts)],
                         ["e3", "a0", "e2", "e1"])

    def test_R14_no_shifts_gives_an_empty_list(self):
        self.assertEqual(compute_payroll([], []), [])
        self.assertEqual(compute_payroll([emp()], []), [])
        self.assertEqual(weekly_breakdown([emp()], []), [])

    # ---- R15 loading --------------------------------------------------------------------------------------------------
    def test_R15_rows_become_shifts_in_file_order(self):
        text = (HEADER + "\n"
                "e1,2024-03-04,09:00,13:00,30\n"
                "e2,2024-03-05,09:00,10:00\n"
                "e1,2024-03-06,09:00,10:00,\n")
        shifts = load_shifts(text)
        self.assertEqual([s.employee_id for s in shifts], ["e1", "e2", "e1"])
        self.assertEqual([s.day.isoformat() for s in shifts], ["2024-03-04", "2024-03-05", "2024-03-06"])
        self.assertEqual([s.paid_minutes for s in shifts], [210, 60, 60])

    def test_R15_blank_lines_and_spaces_are_ignored(self):
        text = ("\n  \n employee_id , day,start ,end,break_min\n\n"
                " e1 , 2024-03-04 , 09:00 , 13:00 , 30 \n   \n")
        (shift,) = load_shifts(text)
        self.assertEqual((shift.employee_id, shift.paid_minutes), ("e1", 210))

    def test_R15_header_only_gives_no_shifts(self):
        self.assertEqual(load_shifts(HEADER + "\n"), [])
        self.assertEqual(load_shifts(HEADER), [])

    def test_R15_the_header_must_be_exact(self):
        for header in ("employee,day,start,end,break_min", "Employee_id,day,start,end,break_min",
                       "employee_id,day,end,start,break_min", HEADER + ",extra",
                       "employee_id,day,start,end"):
            with self.subTest(header=header):
                with self.assertRaises(ValueError) as cm:
                    load_shifts(header + "\ne1,2024-03-04,09:00,13:00\n")
                self.assertTrue(str(cm.exception).startswith("line 1: "), str(cm.exception))

    def test_R15_rows_need_four_or_five_fields(self):
        with self.assertRaises(ValueError) as cm:
            load_shifts(HEADER + "\ne1,2024-03-04,09:00\n")
        self.assertTrue(str(cm.exception).startswith("line 2: "))
        with self.assertRaises(ValueError) as cm:
            load_shifts(HEADER + "\ne1,2024-03-04,09:00,13:00,0\ne1,2024-03-05,09:00,13:00,0,x\n")
        self.assertTrue(str(cm.exception).startswith("line 3: "))

    # ---- R16 error line numbers ------------------------------------------------------------------------------------------
    def test_R16_errors_name_the_line(self):
        cases = [
            ("e1,2024-03-04,09:00,13:00\ne1,2024-02-30,09:00,13:00\n", 3),
            ("e1,2024-03-04,09:00,13:00\ne1,2024-03-05,09:00,13:00\ne1,2024-03-06,25:00,13:00\n", 4),
            ("e1,2024-03-04,09:00,13:00,abc\n", 2),
            ("e1,2024-03-04,09:00,13:00,1.5\n", 2),
        ]
        for body, number in cases:
            with self.subTest(line=number):
                with self.assertRaises(ValueError) as cm:
                    load_shifts(HEADER + "\n" + body)
                self.assertTrue(str(cm.exception).startswith(f"line {number}: "), str(cm.exception))

    def test_R16_problems_that_shift_rejects_are_reported_too(self):
        for row in ("e1,2024-03-04,09:00,09:00", "e1,2024-03-04,09:00,10:00,60",
                    "e1,2024-03-04,09:00,10:00,-5"):
            with self.subTest(row=row):
                with self.assertRaises(ValueError) as cm:
                    load_shifts(HEADER + "\ne1,2024-03-04,09:00,13:00\n" + row + "\n")
                message = str(cm.exception)
                self.assertTrue(message.startswith("line 3: "), message)
                self.assertGreater(len(message), len("line 3: "))

    def test_R16_line_numbers_count_blank_lines_BUG(self):
        with self.assertRaises(ValueError) as cm:
            load_shifts("\n" + HEADER + "\n\ne1,2024-03-04,09:00,17:00,xx\n")
        self.assertTrue(str(cm.exception).startswith("line 4: "), str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            load_shifts("\n\nnot,the,header\n")
        self.assertTrue(str(cm.exception).startswith("line 3: "), str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            load_shifts(HEADER + "\n   \n\ne1,2024-03-04,09:00\n")
        self.assertTrue(str(cm.exception).startswith("line 4: "), str(cm.exception))

    # ---- R17 overlaps ----------------------------------------------------------------------------------------------------------
    def test_R17_overlapping_shifts_are_found(self):
        a = sh("2024-03-04", "09:00", "12:00")
        b = sh("2024-03-04", "11:00", "13:00")
        other = sh("2024-03-04", "11:30", "12:30", emp_id="e2")
        pairs = find_overlaps([a, b, other])
        self.assertEqual(len(pairs), 1)
        self.assertIs(pairs[0][0], a)
        self.assertIs(pairs[0][1], b)

    def test_R17_touching_shifts_do_not_overlap(self):
        self.assertEqual(find_overlaps([sh("2024-03-04", "09:00", "12:00"),
                                        sh("2024-03-04", "12:00", "15:00")]), [])

    def test_R17_different_employees_never_overlap(self):
        self.assertEqual(find_overlaps([sh("2024-03-04", "09:00", "12:00"),
                                        sh("2024-03-04", "09:00", "12:00", emp_id="e2")]), [])

    def test_R17_overnight_shift_runs_into_the_next_day(self):
        night = sh("2024-03-04", "22:00", "06:00")
        early = sh("2024-03-05", "05:00", "09:00")
        later = sh("2024-03-05", "06:00", "09:00")
        pairs = find_overlaps([night, early])
        self.assertEqual([(a is night, b is early) for a, b in pairs], [(True, True)])
        self.assertEqual(find_overlaps([night, later]), [])  # starts exactly when the night ends
        new_year = find_overlaps([sh("2024-12-31", "22:00", "06:00"), sh("2025-01-01", "05:00", "07:00")])
        self.assertEqual(len(new_year), 1)

    def test_R17_pairs_are_ordered_by_position(self):
        s0 = sh("2024-03-04", "09:00", "12:00")
        s1 = sh("2024-03-04", "10:00", "13:00")
        s2 = sh("2024-03-04", "11:00", "14:00")
        pairs = find_overlaps([s0, s1, s2])
        self.assertEqual([(a is x, b is y) for (a, b), (x, y) in
                          zip(pairs, [(s0, s1), (s0, s2), (s1, s2)])], [(True, True)] * 3)
        self.assertEqual(len(pairs), 3)

    def test_R17_no_or_one_shift(self):
        self.assertEqual(find_overlaps([]), [])
        self.assertEqual(find_overlaps([sh("2024-03-04", "09:00", "12:00")]), [])


if __name__ == "__main__":
    unittest.main()
