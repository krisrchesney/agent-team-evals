import unittest

from paykit import (Employee, PayRow, Shift, compute_payroll, find_overlaps, load_shifts,
                    render_text, weekly_breakdown)
from paykit.money import format_cents


class TestPaykit(unittest.TestCase):
    def test_simple_week(self):
        ann = Employee("e1", "Ann Lee", [("2024-01-01", 2000)])
        shifts = [Shift("e1", "2024-03-04", "09:00", "17:00", 60),
                  Shift("e1", "2024-03-05", "09:00", "17:00", 60)]
        rows = compute_payroll([ann], shifts)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].regular_minutes, 840)
        self.assertEqual(rows[0].gross_cents, 28000)

    def test_overnight_shift(self):
        shift = Shift("e1", "2024-03-04", "22:00", "06:00", 60)
        self.assertEqual(shift.duration, 480)
        self.assertEqual(shift.paid_minutes, 420)

    def test_load_shifts(self):
        text = "employee_id,day,start,end,break_min\ne1,2024-03-04,09:00,17:00,30\n"
        (shift,) = load_shifts(text)
        self.assertEqual(shift.paid_minutes, 450)

    def test_text_report_has_title(self):
        out = render_text([PayRow("e1", "Ann Lee", 2310, 150, 123456)])
        self.assertTrue(out.startswith("Payroll report\n"))
        self.assertIn("$1,234.56", out)

    def test_bad_time(self):
        with self.assertRaises(ValueError):
            Shift("e1", "2024-03-04", "25:00", "17:00")

    def test_touching_shifts_do_not_overlap(self):
        a = Shift("e1", "2024-03-04", "09:00", "12:00")
        b = Shift("e1", "2024-03-04", "12:00", "15:00")
        self.assertEqual(find_overlaps([a, b]), [])

    def test_load_error_names_the_line(self):
        text = "employee_id,day,start,end,break_min\ne1,2024-03-04,09:00,17:00,xx\n"
        with self.assertRaises(ValueError) as cm:
            load_shifts(text)
        self.assertTrue(str(cm.exception).startswith("line 2:"))

    def test_money_format(self):
        self.assertEqual(format_cents(123456), "$1,234.56")
        self.assertEqual(format_cents(0), "$0.00")

    def test_weekly_breakdown_one_row_per_week(self):
        ann = Employee("e1", "Ann Lee", [("2024-01-01", 2000)])
        shifts = [Shift("e1", "2024-03-04", "09:00", "12:00"),
                  Shift("e1", "2024-03-11", "09:00", "12:00")]
        rows = weekly_breakdown([ann], shifts)
        self.assertEqual([row.week_start.isoformat() for row in rows],
                         ["2024-03-04", "2024-03-11"])


if __name__ == "__main__":
    unittest.main()
