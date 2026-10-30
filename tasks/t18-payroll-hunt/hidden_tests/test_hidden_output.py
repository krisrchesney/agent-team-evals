"""Hidden grader for t18, part 3: formatting, reports, CSV and the command line (R18 to R27).
Tests are named after the requirement they check. Fixtures use hours with a fractional part so
that a test only depends on the hours rule (R19) when it says so."""
import contextlib
import io
import json
import os
import tempfile
import unittest

from paykit import PayRow, WeekRow, cli, compute_payroll, load_shifts
from paykit.money import format_cents, format_hours
from paykit.report import render_text, render_weekly

from ._common import HEADER, day

ANN = PayRow("e1", "Ann Lee", 2300, 145, 123456)   # 38.33 h, 2.42 h overtime, $1,234.56
BOB = PayRow("e2", "Bob", 1841, 70, 98765)          # 30.68 h, 1.17 h overtime, $987.65

TEXT = (
    "Payroll report\n"
    "==============\n"
    "Employee      Reg hrs  OT hrs         Gross\n"
    "------------  -------  ------  ------------\n"
    "Ann Lee         38.33    2.42     $1,234.56\n"
    "Bob             30.68    1.17       $987.65\n"
    "------------  -------  ------  ------------\n"
    "TOTAL           69.02    3.58     $2,222.21\n"
    "2 employees\n"
)

WEEKLY = (
    "Weekly breakdown\n"
    "================\n"
    "Employee      Week of     Reg hrs  OT hrs         Gross\n"
    "------------  ----------  -------  ------  ------------\n"
    "Ann Lee       2024-03-04    38.33    2.42     $1,234.56\n"
    "Bob           2024-03-11    30.68    1.17       $987.65\n"
)


def pay_row(name, gross=100005, emp_id="e9"):
    return PayRow(emp_id, name, 2300, 145, gross)


def render(rows, *args, **kwargs):
    """`render` is new in this task, so it is imported when used."""
    from paykit.report import render as real_render
    return real_render(rows, *args, **kwargs)


class HiddenOutput(unittest.TestCase):
    # ---- R18 money ----------------------------------------------------------------------------------
    def test_R18_format_cents(self):
        table = {0: "$0.00", 5: "$0.05", 99: "$0.99", 100: "$1.00", 123456: "$1,234.56",
                 100000: "$1,000.00", 99999: "$999.99", 100000000: "$1,000,000.00"}
        for cents, want in table.items():
            with self.subTest(cents=cents):
                self.assertEqual(format_cents(cents), want)

    def test_R18_negative_amounts_put_the_sign_before_the_dollar_sign(self):
        self.assertEqual(format_cents(-500), "-$5.00")
        self.assertEqual(format_cents(-5), "-$0.05")
        self.assertEqual(format_cents(-123456), "-$1,234.56")

    # ---- R19 hours ----------------------------------------------------------------------------------
    def test_R19_hours_always_have_two_decimals_BUG(self):
        table = {450: "7.50", 0: "0.00", 480: "8.00", 75: "1.25", 2400: "40.00", 75000: "1250.00",
                 15: "0.25"}
        for minutes, want in table.items():
            with self.subTest(minutes=minutes):
                self.assertEqual(format_hours(minutes), want)

    def test_R19_hours_that_are_not_quarters(self):
        self.assertEqual(format_hours(20), "0.33")
        self.assertEqual(format_hours(100), "1.67")
        self.assertEqual(format_hours(40), "0.67")
        self.assertEqual(format_hours(6035), "100.58")

    # ---- R20 text report layout -------------------------------------------------------------------------
    def test_R20_full_text_report(self):
        self.assertEqual(render_text([ANN, BOB]), TEXT)

    def test_R20_columns_have_the_stated_widths_and_alignment(self):
        lines = render_text([ANN, BOB]).split("\n")
        self.assertEqual(lines[0], "Payroll report")
        self.assertEqual(lines[1], "=" * 14)
        for line in lines[2:8]:
            self.assertEqual(len(line), 12 + 2 + 7 + 2 + 6 + 2 + 12, line)
            self.assertEqual(line[12:14], "  ")
            self.assertEqual(line[21:23], "  ")
            self.assertEqual(line[29:31], "  ")
        header, rule, ann = lines[2], lines[3], lines[4]
        self.assertEqual(rule, "-" * 12 + "  " + "-" * 7 + "  " + "-" * 6 + "  " + "-" * 12)
        self.assertEqual([header[:12].rstrip(), header[14:21].strip(), header[23:29].strip(),
                          header[31:].strip()], ["Employee", "Reg hrs", "OT hrs", "Gross"])
        self.assertEqual(header[:12], "Employee    ")
        self.assertEqual(header[14:21], "Reg hrs")
        self.assertEqual(header[31:], "       Gross")
        self.assertEqual(ann[:12], "Ann Lee     ")
        self.assertEqual(ann[14:21], "  38.33")
        self.assertEqual(ann[23:29], "  2.42")
        self.assertEqual(ann[31:], "   $1,234.56")

    def test_R20_lines_end_with_newline_without_trailing_spaces(self):
        out = render_text([ANN, BOB])
        self.assertTrue(out.endswith("employees\n"))
        self.assertFalse(out.endswith("\n\n"))
        for line in out.split("\n"):
            self.assertEqual(line, line.rstrip())

    # ---- R21 names ------------------------------------------------------------------------------------------
    def test_R21_long_names_are_shortened(self):
        out = render_text([pay_row("Alexandria Montgomery"), pay_row("Thirteen_chrs", emp_id="e8")])
        self.assertIn("Alexandri...  ", out)
        self.assertIn("Thirteen_...  ", out)
        self.assertNotIn("Montgomery", out)

    def test_R21_twelve_character_names_are_written_in_full(self):
        out = render_text([pay_row("Exactly12chr")])
        self.assertIn("Exactly12chr  ", out)
        self.assertNotIn("...", out)

    def test_R21_short_names_are_padded_not_changed(self):
        out = render_text([pay_row("Al"), pay_row("Eleven_chars", emp_id="e8")])
        self.assertIn("\nAl            ", out)
        self.assertIn("\nEleven_chars  ", out)

    # ---- R22 totals and count --------------------------------------------------------------------------------
    def test_R22_total_row_sums_everything(self):
        total = render_text([ANN, BOB]).split("\n")[7]
        self.assertEqual(total, "TOTAL           69.02    3.58     $2,222.21")

    def test_R22_total_uses_thousands_separators(self):
        rows = [pay_row("A", 100000000, "e1"), pay_row("B", 50, "e2")]
        total = [line for line in render_text(rows).split("\n") if line.startswith("TOTAL")]
        self.assertEqual(len(total), 1)
        self.assertTrue(total[0].endswith("$1,000,000.50"), total[0])

    def test_R22_count_line_is_singular_or_plural(self):
        self.assertTrue(render_text([ANN]).endswith("\n1 employee\n"))
        self.assertTrue(render_text([ANN, BOB]).endswith("\n2 employees\n"))
        self.assertTrue(render_text([ANN] * 3).endswith("\n3 employees\n"))

    # ---- R23 empty -----------------------------------------------------------------------------------------------
    def test_R23_report_without_rows(self):
        self.assertEqual(render_text([]), "Payroll report\n==============\nNo shifts.\n")

    # ---- R24 weekly report -------------------------------------------------------------------------------------
    def test_R24_weekly_report_layout(self):
        rows = [WeekRow("e1", "Ann Lee", day("2024-03-04"), 2300, 145, 123456),
                WeekRow("e2", "Bob", day("2024-03-11"), 1841, 70, 98765)]
        self.assertEqual(render_weekly(rows), WEEKLY)

    def test_R24_weekly_report_shortens_long_names(self):
        out = render_weekly([WeekRow("e1", "Alexandria Montgomery", day("2024-03-04"), 2300, 145, 100)])
        self.assertIn("\nAlexandri...  2024-03-04  ", out)
        self.assertTrue(out.endswith("$1.00\n"))

    def test_R24_weekly_report_without_rows(self):
        self.assertEqual(render_weekly([]), "Weekly breakdown\n================\nNo shifts.\n")

    # ---- R25 render ---------------------------------------------------------------------------------------------------
    def test_R25_default_format_is_text(self):
        self.assertEqual(render([ANN, BOB]), TEXT)
        self.assertEqual(render([ANN, BOB], "text"), TEXT)
        self.assertEqual(render([ANN, BOB], fmt="text"), render_text([ANN, BOB]))
        self.assertEqual(render([]), render_text([]))

    def test_R25_unknown_format(self):
        for bad in ("xml", "CSV", "", None):
            with self.subTest(fmt=bad):
                with self.assertRaises(ValueError) as cm:
                    render([ANN], bad)
                self.assertEqual(str(cm.exception), f"unknown format {bad!r}")

    def test_R25_text_report_is_unchanged_by_the_feature(self):
        self.assertEqual(render_text([ANN, BOB]), TEXT)
        self.assertEqual(render_text([pay_row("Alexandria Montgomery")]).count("\n"), 8)

    # ---- R26 csv ---------------------------------------------------------------------------------------------------------
    def test_R26_csv_layout(self):
        self.assertEqual(render([ANN, BOB], "csv"),
                         "employee_id,name,regular_hours,overtime_hours,gross\n"
                         "e1,Ann Lee,38.33,2.42,1234.56\n"
                         "e2,Bob,30.68,1.17,987.65\n")

    def test_R26_gross_is_plain_dollars(self):
        for cents, want in ((5, "0.05"), (100000, "1000.00"), (123456789, "1234567.89"),
                            (100, "1.00")):
            with self.subTest(cents=cents):
                self.assertTrue(render([pay_row("A", cents)], "csv").endswith("," + want + "\n"))

    def test_R26_fields_with_special_characters_are_quoted(self):
        rows = [PayRow("a,1", "Smith, Jo", 2300, 145, 100005),
                PayRow("e3", 'Al "Al" B', 2300, 145, 100005),
                PayRow("e4", "Two\nLines", 2300, 145, 100005),
                PayRow("e5", "Car\rReturn", 2300, 145, 100005),
                PayRow("e6", "Plain Name", 2300, 145, 100005)]
        lines = render([rows[0]], "csv").split("\n")
        self.assertEqual(lines[1], '"a,1","Smith, Jo",38.33,2.42,1000.05')
        self.assertEqual(render([rows[1]], "csv").split("\n")[1], 'e3,"Al ""Al"" B",38.33,2.42,1000.05')
        self.assertEqual(render([rows[2]], "csv"),
                         "employee_id,name,regular_hours,overtime_hours,gross\n"
                         'e4,"Two\nLines",38.33,2.42,1000.05\n')
        self.assertIn('e5,"Car\rReturn",', render([rows[3]], "csv"))
        self.assertIn("e6,Plain Name,38.33", render([rows[4]], "csv"))

    def test_R26_names_are_not_shortened(self):
        self.assertIn(",Alexandria Montgomery,", render([pay_row("Alexandria Montgomery")], "csv"))

    def test_R26_no_rows_gives_only_the_header(self):
        self.assertEqual(render([], "csv"), "employee_id,name,regular_hours,overtime_hours,gross\n")

    # ---- R27 command line ------------------------------------------------------------------------------------------------
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.shifts = self.write("shifts.csv", HEADER + "\ne1,2024-03-04,08:00,16:15,30\n")
        self.employees = self.write("employees.json", json.dumps(
            [{"id": "e1", "name": "Ann Lee", "rates": [["2024-01-01", 2000]]}]))

    def write(self, name, text):
        path = os.path.join(self.dir.name, name)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        return path

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def expected_rows(self):
        from paykit import Employee
        employees = [Employee("e1", "Ann Lee", [("2024-01-01", 2000)])]
        with open(self.shifts, encoding="utf-8") as handle:
            return compute_payroll(employees, load_shifts(handle.read()))

    def test_R27_prints_the_text_report(self):
        code, out, err = self.run_cli([self.shifts, self.employees])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, render_text(self.expected_rows()))
        self.assertIn("$155.00", out)
        self.assertIn("Ann Lee", out)

    def test_R27_format_option(self):
        want = render(self.expected_rows(), "csv")
        for argv in (["--format", "csv", self.shifts, self.employees],
                     [self.shifts, "--format", "csv", self.employees],
                     [self.shifts, self.employees, "--format", "csv"]):
            with self.subTest(argv=argv[:2]):
                code, out, err = self.run_cli(argv)
                self.assertEqual((code, err, out), (0, "", want))
        self.assertIn(",155.00\n", want)
        code, out, _ = self.run_cli([self.shifts, self.employees, "--format", "text"])
        self.assertEqual((code, out), (0, render_text(self.expected_rows())))

    def test_R27_wrong_arguments_print_the_usage(self):
        usage = "error: usage: paykit SHIFTS.csv EMPLOYEES.json [--format text|csv]\n"
        for argv in ([], [self.shifts], [self.shifts, self.employees, "extra"],
                     [self.shifts, self.employees, "--format"]):
            with self.subTest(argv=argv):
                self.assertEqual(self.run_cli(argv), (2, "", usage))

    def test_R27_unknown_format_and_unknown_employee(self):
        self.assertEqual(self.run_cli([self.shifts, self.employees, "--format", "xml"]),
                         (2, "", "error: unknown format 'xml'\n"))
        other = self.write("other.csv", HEADER + "\nzz,2024-03-04,08:00,16:15,30\n")
        self.assertEqual(self.run_cli([other, self.employees]),
                         (2, "", "error: unknown employee 'zz'\n"))

    def test_R27_unreadable_or_malformed_input(self):
        bad_shifts = self.write("bad.csv", HEADER + "\ne1,2024-03-04,08:00,16:15,30\ne1,nope,08:00,16:15\n")
        bad_json = self.write("bad.json", "{not json")
        missing = os.path.join(self.dir.name, "missing.csv")
        code, out, err = self.run_cli([bad_shifts, self.employees])
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("error: line 3: "), err)
        for argv in ([missing, self.employees], [self.shifts, bad_json],
                     [self.shifts, os.path.join(self.dir.name, "missing.json")]):
            with self.subTest(argv=argv[1][-12:]):
                code, out, err = self.run_cli(argv)
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("error: "), err)
                self.assertEqual(err.count("\n"), 1)

    def test_R27_overlaps_are_warned_about_and_the_report_still_prints(self):
        shifts = self.write("overlap.csv", HEADER + "\n"
                            "e1,2024-03-04,08:00,12:00\n"
                            "e1,2024-03-04,11:00,15:00\n"
                            "e1,2024-03-05,08:00,12:00\n"
                            "e1,2024-03-05,11:00,15:00\n")
        code, out, err = self.run_cli([shifts, self.employees])
        self.assertEqual(code, 0)
        self.assertEqual(err, "warning: overlapping shifts for e1 on 2024-03-04\n"
                              "warning: overlapping shifts for e1 on 2024-03-05\n")
        self.assertTrue(out.startswith("Payroll report\n"))
        self.assertTrue(out.endswith("1 employee\n"))


if __name__ == "__main__":
    unittest.main()
