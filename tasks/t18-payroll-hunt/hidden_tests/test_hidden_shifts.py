"""Hidden grader for t18, part 1: shifts, employees and rates (R1 to R8). Tests are named after
the requirement they check; the ones marked BUG isolate one planted bug each."""
import datetime
import unittest

from paykit import Employee, Shift, compute_payroll

from ._common import emp, end_after, sh


class HiddenShifts(unittest.TestCase):
    # ---- R1 -------------------------------------------------------------------------------------
    def test_R1_valid_shift(self):
        s = sh("2024-03-04", "09:00", "17:30")
        self.assertEqual(s.day, datetime.date(2024, 3, 4))
        self.assertEqual(s.duration, 510)
        self.assertEqual(s.employee_id, "e1")

    def test_R1_clock_limits_are_allowed(self):
        self.assertEqual(sh("2024-03-04", "00:00", "23:59").duration, 23 * 60 + 59)
        self.assertEqual(sh("2024-02-29", "00:00", "00:01").duration, 1)

    def test_R1_bad_times_are_rejected(self):
        for bad in ("9:00", "09:0", "24:00", "12:60", "aa:bb", "09:00:00", " 09:00", "", 900, None):
            with self.subTest(start=bad):
                with self.assertRaises(ValueError):
                    Shift("e1", "2024-03-04", bad, "17:00")
            with self.subTest(end=bad):
                with self.assertRaises(ValueError):
                    Shift("e1", "2024-03-04", "08:00", bad)

    def test_R1_bad_days_are_rejected(self):
        for bad in ("2024-02-30", "2024-13-01", "24-03-04", "2024/03/04", "2024-3-4", "", None,
                    20240304, "2023-02-29"):
            with self.subTest(day=bad):
                with self.assertRaises(ValueError):
                    Shift("e1", bad, "09:00", "17:00")

    # ---- R2 -------------------------------------------------------------------------------------
    def test_R2_overnight_shift_ends_next_day(self):
        self.assertEqual(sh("2024-03-04", "22:00", "06:00").duration, 480)
        self.assertEqual(sh("2024-03-04", "23:59", "00:00").duration, 1)
        self.assertEqual(sh("2024-03-04", "12:00", "11:59").duration, 24 * 60 - 1)

    def test_R2_same_day_shift_duration(self):
        self.assertEqual(sh("2024-03-04", "08:00", "09:15").duration, 75)

    def test_R2_equal_start_and_end_is_rejected(self):
        for t in ("00:00", "09:00", "23:59"):
            with self.subTest(time=t):
                with self.assertRaises(ValueError):
                    sh("2024-03-04", t, t)

    # ---- R3 -------------------------------------------------------------------------------------
    def test_R3_break_must_be_shorter_than_the_shift(self):
        for bad in (60, 61, 600):
            with self.subTest(break_min=bad):
                with self.assertRaises(ValueError):
                    sh("2024-03-04", "09:00", "10:00", bad)
        self.assertEqual(sh("2024-03-04", "09:00", "10:00", 59).duration, 60)

    def test_R3_break_must_be_a_non_negative_int(self):
        for bad in (-1, 1.5, "30", True, None):
            with self.subTest(break_min=bad):
                with self.assertRaises(ValueError):
                    sh("2024-03-04", "09:00", "10:00", bad)

    def test_R3_break_defaults_to_zero(self):
        self.assertEqual(sh("2024-03-04", "09:00", "10:00").paid_minutes, 60)

    # ---- R4 -------------------------------------------------------------------------------------
    def test_R4_recorded_break_is_deducted(self):
        self.assertEqual(sh("2024-03-04", "09:00", "13:00", 30).paid_minutes, 210)
        self.assertEqual(sh("2024-03-04", "09:00", "13:00", 60).paid_minutes, 180)

    def test_R4_long_shift_gets_at_least_the_automatic_break(self):
        for brk, want in ((0, 390), (10, 390), (29, 390), (30, 390), (45, 375)):
            with self.subTest(break_min=brk):
                self.assertEqual(sh("2024-03-04", "09:00", "16:00", brk).paid_minutes, want)

    def test_R4_exactly_six_hours_gets_no_automatic_break_BUG(self):
        self.assertEqual(sh("2024-03-04", "09:00", "15:00").paid_minutes, 360)
        self.assertEqual(sh("2024-03-04", "09:00", "15:00", 10).paid_minutes, 345)  # 350 rounds down
        self.assertEqual(sh("2024-03-04", "09:00", "15:01").paid_minutes, 330)      # 361 - 30 = 331

    def test_R4_automatic_break_applies_to_overnight_shifts(self):
        self.assertEqual(sh("2024-03-04", "22:00", "06:00").paid_minutes, 450)
        self.assertEqual(sh("2024-03-04", "22:00", "04:00").paid_minutes, 360)

    def test_R4_short_shifts_are_not_given_a_break(self):
        self.assertEqual(sh("2024-03-04", "09:00", "14:00").paid_minutes, 300)

    # ---- R5 -------------------------------------------------------------------------------------
    def test_R5_rounds_to_the_nearest_quarter_hour(self):
        table = {7: 0, 8: 15, 14: 15, 15: 15, 22: 15, 23: 30, 37: 30, 38: 45, 60: 60, 67: 60,
                 68: 75}
        for minutes, want in table.items():
            with self.subTest(minutes=minutes):
                self.assertEqual(sh("2024-03-04", "09:00", end_after(minutes)).paid_minutes, want)

    def test_R5_rounding_comes_after_the_break(self):
        self.assertEqual(sh("2024-03-04", "09:00", "12:10", 20).paid_minutes, 165)  # 170 -> 165
        self.assertEqual(sh("2024-03-04", "09:00", "12:10", 10).paid_minutes, 180)  # 180

    # ---- R6 -------------------------------------------------------------------------------------
    def test_R6_invalid_employee_arguments(self):
        good = [("2024-01-01", 2000)]
        bad_cases = [
            ("", "Ann", good), (None, "Ann", good), (5, "Ann", good),
            ("e1", "", good), ("e1", "   ", good), ("e1", None, good),
            ("e1", "Ann", []),
            ("e1", "Ann", [("2024-01-01", 0)]), ("e1", "Ann", [("2024-01-01", -5)]),
            ("e1", "Ann", [("2024-01-01", 15.5)]), ("e1", "Ann", [("2024-01-01", "20")]),
            ("e1", "Ann", [("2024-01-01", True)]),
            ("e1", "Ann", [("2024-02-30", 2000)]), ("e1", "Ann", [("tomorrow", 2000)]),
            ("e1", "Ann", [("2024-01-01", 2000), ("2024-06-01", 0)]),
        ]
        for args in bad_cases:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    Employee(*args)

    def test_R6_valid_employees(self):
        self.assertEqual(Employee("e1", "Ann", [["2024-01-01", 2000]]).rate_on("2024-05-05"), 2000)
        self.assertEqual(Employee("e1", "A", [("2024-01-01", 1)]).rate_on("2024-01-01"), 1)

    # ---- R7 -------------------------------------------------------------------------------------
    def test_R7_rate_takes_effect_on_its_effective_day(self):
        e = emp(rates=[("2024-01-01", 2000), ("2024-03-07", 3000)])
        self.assertEqual(e.rate_on("2024-03-06"), 2000)
        self.assertEqual(e.rate_on("2024-03-07"), 3000)
        self.assertEqual(e.rate_on("2024-12-31"), 3000)
        self.assertEqual(e.rate_on("2024-01-01"), 2000)

    def test_R7_day_before_the_first_rate_is_an_error(self):
        e = emp(rates=[("2024-01-01", 2000)])
        with self.assertRaises(ValueError):
            e.rate_on("2023-12-31")

    def test_R7_rates_may_be_given_in_any_order_BUG(self):
        e = emp(rates=[("2024-06-01", 3000), ("2024-01-01", 2000)])
        self.assertEqual(e.rate_on("2024-07-01"), 3000)
        self.assertEqual(e.rate_on("2024-03-01"), 2000)
        e = emp(rates=[("2024-05-01", 2500), ("2024-01-01", 2000), ("2024-09-01", 3000),
                       ("2024-03-01", 2200)])
        self.assertEqual(e.rate_on("2024-02-01"), 2000)
        self.assertEqual(e.rate_on("2024-04-15"), 2200)
        self.assertEqual(e.rate_on("2024-05-01"), 2500)
        self.assertEqual(e.rate_on("2024-10-01"), 3000)
        with self.assertRaises(ValueError):
            e.rate_on("2023-12-31")

    # ---- R8 -------------------------------------------------------------------------------------
    def test_R8_inputs_are_never_modified(self):
        rates = [("2024-06-01", 3000), ("2024-01-01", 2000)]
        rates_before = list(rates)
        e = Employee("e1", "Ann", rates)
        e.rate_on("2024-07-01")
        self.assertEqual(rates, rates_before)
        employees = [e, emp("e2", "Bob")]
        shifts = [sh("2024-03-05", "09:00", "12:00"), sh("2024-03-04", "09:00", "12:00", emp_id="e2"),
                  sh("2024-03-04", "09:00", "12:00")]
        employees_before, shifts_before = list(employees), list(shifts)
        compute_payroll(employees, shifts)
        self.assertEqual(rates, rates_before)
        self.assertEqual(len(employees), 2)
        self.assertTrue(all(a is b for a, b in zip(employees, employees_before)))
        self.assertTrue(all(a is b for a, b in zip(shifts, shifts_before)))
        self.assertEqual(len(shifts), 3)


if __name__ == "__main__":
    unittest.main()
