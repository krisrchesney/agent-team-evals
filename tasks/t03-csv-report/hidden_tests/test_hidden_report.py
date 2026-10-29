import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from csvreport.cli import main

SALES = (
    "region,rep,amount\n"
    "North,ann,10\n"
    "North,bob,20.5\n"
    "South,ann,5\n"
    "South,cy,-2\n"
    "East,bob,7\n"
)


class HiddenReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text, name="data.csv"):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write(text)
        return path

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = main(argv)
            except SystemExit as e:
                code = 0 if e.code is None else e.code
        return code, out.getvalue().splitlines(), err.getvalue()

    def report(self, text, *args):
        code, lines, err = self.run_cli([self.write(text), "--group-by", "region", *args])
        self.assertEqual(code, 0, err)
        return lines

    # Requirement 1: --agg and --value, --sum alias, usage errors

    def test_r1_sum_alias_unchanged(self):
        self.assertEqual(self.report(SALES, "--sum", "amount"),
                         ["region,sum_amount", "East,7.00", "North,30.50", "South,3.00"])

    def test_r1_value_defaults_to_sum(self):
        self.assertEqual(self.report(SALES, "--value", "amount"),
                         ["region,sum_amount", "East,7.00", "North,30.50", "South,3.00"])

    def test_r1_mean(self):
        self.assertEqual(self.report(SALES, "--agg", "mean", "--value", "amount"),
                         ["region,mean_amount", "East,7.00", "North,15.25", "South,1.50"])

    def test_r1_min_and_max(self):
        self.assertEqual(self.report(SALES, "--agg", "min", "--value", "amount")[1:],
                         ["East,7.00", "North,10.00", "South,-2.00"])
        self.assertEqual(self.report(SALES, "--agg", "max", "--value", "amount")[1:],
                         ["East,7.00", "North,20.50", "South,5.00"])

    def test_r1_count_needs_no_value(self):
        self.assertEqual(self.report(SALES, "--agg", "count"),
                         ["region,count", "East,1", "North,2", "South,2"])

    def test_r1_count_ignores_value(self):
        text = "region,amount\nNorth,abc\nNorth,1\n"
        self.assertEqual(self.report(text, "--agg", "count", "--value", "amount"),
                         ["region,count", "North,2"])

    def test_r1_sum_with_agg_is_usage_error(self):
        path = self.write(SALES)
        code, lines, _ = self.run_cli([path, "--group-by", "region", "--sum", "amount",
                                       "--agg", "mean"])
        self.assertEqual(code, 2)
        self.assertEqual(lines, [])

    def test_r1_sum_with_value_is_usage_error(self):
        path = self.write(SALES)
        code, _, _ = self.run_cli([path, "--group-by", "region", "--sum", "amount",
                                   "--value", "amount"])
        self.assertEqual(code, 2)

    def test_r1_missing_value_is_usage_error(self):
        path = self.write(SALES)
        code, lines, _ = self.run_cli([path, "--group-by", "region", "--agg", "mean"])
        self.assertEqual(code, 2)
        self.assertEqual(lines, [])

    # Requirement 2: header label and number format

    def test_r2_two_decimals_and_rounding(self):
        text = "region,amount\nWest,1.005e1\nWest,0.333\n"
        self.assertEqual(self.report(text, "--agg", "max", "--value", "amount"),
                         ["region,max_amount", "West,10.05"])
        self.assertEqual(self.report(text, "--agg", "min", "--value", "amount"),
                         ["region,min_amount", "West,0.33"])

    def test_r2_groups_sorted(self):
        text = "region,amount\nb,1\na,1\nc,1\n"
        self.assertEqual([l.split(",")[0] for l in self.report(text, "--agg", "count")[1:]],
                         ["a", "b", "c"])

    # Requirement 3: whitespace stripping, all-empty rows skipped

    def test_r3_strips_header_and_cells(self):
        text = " region , amount \n North , 10 \nNorth,5\n"
        self.assertEqual(self.report(text, "--value", "amount"),
                         ["region,sum_amount", "North,15.00"])

    def test_r3_all_empty_rows_skipped(self):
        text = "region,amount\nNorth,1\n,\n  ,  \n\nNorth,2\n"
        self.assertEqual(self.report(text, "--agg", "count"),
                         ["region,count", "North,2"])

    # Requirement 4: empty value cells

    def test_r4_empty_cells_skipped_but_counted(self):
        text = "region,amount\nNorth,10\nNorth,\nNorth,20\n"
        self.assertEqual(self.report(text, "--agg", "mean", "--value", "amount")[1:],
                         ["North,15.00"])
        self.assertEqual(self.report(text, "--agg", "count")[1:], ["North,3"])

    def test_r4_group_with_no_values(self):
        text = "region,amount\nNorth,4\nSouth,\nSouth, \n"
        self.assertEqual(self.report(text, "--sum", "amount")[1:], ["North,4.00", "South,0.00"])
        for agg in ("mean", "min", "max"):
            self.assertEqual(self.report(text, "--agg", agg, "--value", "amount")[1:],
                             ["North,4.00", "South,"], agg)

    # Requirement 5: bad numbers

    def test_r5_bad_number_message_and_line(self):
        path = self.write("region,amount\nNorth,10\n\nSouth,abc\nEast,xyz\n")
        code, lines, err = self.run_cli([path, "--group-by", "region", "--sum", "amount"])
        self.assertEqual(code, 2)
        self.assertEqual(lines, [])
        self.assertEqual(err.strip(),
                         f"csvreport: error: {path}:4: bad number 'abc' in column 'amount'")

    def test_r5_bad_number_is_stripped_in_message(self):
        path = self.write("region,amount\nNorth, 1x \n")
        code, _, err = self.run_cli([path, "--group-by", "region", "--agg", "mean",
                                     "--value", "amount"])
        self.assertEqual(code, 2)
        self.assertIn(f"{path}:2: bad number '1x' in column 'amount'", err)

    # Requirement 6: missing columns

    def test_r6_missing_group_by_column(self):
        path = self.write(SALES)
        code, lines, err = self.run_cli([path, "--group-by", "city", "--sum", "amount"])
        self.assertEqual(code, 2)
        self.assertEqual(lines, [])
        self.assertEqual(err.strip(), "csvreport: error: no column 'city'")

    def test_r6_missing_value_column(self):
        path = self.write(SALES)
        code, _, err = self.run_cli([path, "--group-by", "region", "--agg", "max",
                                     "--value", "price"])
        self.assertEqual(code, 2)
        self.assertEqual(err.strip(), "csvreport: error: no column 'price'")

    def test_r6_missing_where_column(self):
        path = self.write(SALES)
        code, _, err = self.run_cli([path, "--group-by", "region", "--sum", "amount",
                                     "--where", "year=2024"])
        self.assertEqual(code, 2)
        self.assertEqual(err.strip(), "csvreport: error: no column 'year'")

    # Requirement 7: --where

    def test_r7_single_where(self):
        self.assertEqual(self.report(SALES, "--sum", "amount", "--where", "rep=ann"),
                         ["region,sum_amount", "North,10.00", "South,5.00"])

    def test_r7_where_all_must_match(self):
        self.assertEqual(self.report(SALES, "--agg", "count", "--where", "rep=bob",
                                     "--where", "region=North"),
                         ["region,count", "North,1"])

    def test_r7_where_splits_on_first_equals(self):
        text = "region,note,amount\nNorth,a=b,1\nNorth,a,2\n"
        self.assertEqual(self.report(text, "--sum", "amount", "--where", "note=a=b")[1:],
                         ["North,1.00"])

    def test_r7_where_matches_stripped_cell(self):
        text = "region,rep,amount\nNorth, ann ,3\nNorth,annie,4\n"
        self.assertEqual(self.report(text, "--sum", "amount", "--where", "rep=ann")[1:],
                         ["North,3.00"])

    def test_r7_filtered_rows_not_checked(self):
        text = "region,rep,amount\nNorth,ann,1\nNorth,bob,oops\n"
        self.assertEqual(self.report(text, "--sum", "amount", "--where", "rep=ann")[1:],
                         ["North,1.00"])

    # Requirement 8: --delimiter

    def test_r8_delimiter(self):
        text = "region;amount\nNorth, East;1,5\nNorth, East;2\n".replace("1,5", "1.5")
        self.assertEqual(self.report(text, "--sum", "amount", "--delimiter", ";"),
                         ["region,sum_amount", '"North, East",3.50'])

    # Requirement 9: quoting in the report

    def test_r9_quotes_fields(self):
        text = 'region,amount\n"North, East",1\n"say ""hi""",2\nplain,3\n'
        self.assertEqual(self.report(text, "--sum", "amount"),
                         ["region,sum_amount", '"North, East",1.00', "plain,3.00",
                          '"say ""hi""",2.00'])

    # Requirement 10: exit status

    def test_r10_success_returns_zero(self):
        code, _, err = self.run_cli([self.write(SALES), "--group-by", "rep", "--agg", "count"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
