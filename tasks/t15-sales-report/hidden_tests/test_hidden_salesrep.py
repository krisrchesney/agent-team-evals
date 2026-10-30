import contextlib
import csv
import io
import json
import os
import re
import tempfile
import unittest

from salesrep.cli import main

HEADER = "id,date,region,product,qty,unit_price,discount_pct,currency,status"


def row(id, region="East", product="Pen", qty=1, price="10.00", date="2024-01-15", disc="0",
        cur="USD", status="paid"):
    return f"{id},{date},{region},{product},{qty},{price},{disc},{cur},{status}"


def text(*rows):
    return HEADER + "\n" + "\n".join(rows) + "\n"


def cells(line):
    return re.split(r"\s{2,}", line.strip())


class Base(unittest.TestCase):
    def run_cli(self, csv_text, *args):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, "sales.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(csv_text)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main([path, *args])
            except SystemExit as e:  # argparse
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def table(self, csv_text, *args):
        code, out, err = self.run_cli(csv_text, *args)
        self.assertEqual(code, 0, err)
        return out

    def json_rows(self, csv_text, *args):
        code, out, err = self.run_cli(csv_text, "--json", *args)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def body(self, csv_text, *args):
        """Table data lines between the two rules, as lists of cells, plus the TOTAL cells."""
        lines = self.table(csv_text, *args).splitlines()
        rules = [i for i, l in enumerate(lines) if l and set(l) <= {"-", " "}]
        data = [cells(l) for l in lines[rules[0] + 1: rules[1]]]
        return data, cells(lines[rules[1] + 1])


class HiddenSalesReport(Base):
    # R1: rounding of discounts and conversions

    def test_r1_discounted_unit_price_is_rounded_before_quantity(self):
        d = self.json_rows(text(row(1, qty=3, price="0.35", disc="10")))
        self.assertEqual(d["rows"][0]["revenue"], "0.96")  # 0.315 -> 0.32, times 3

    def test_r1_unit_price_rounds_half_up_not_half_even(self):
        d = self.json_rows(text(row(1, price="1.25", disc="50")))
        self.assertEqual(d["rows"][0]["revenue"], "0.63")

    def test_r1_each_row_is_converted_and_rounded_on_its_own(self):
        d = self.json_rows(text(row(1, price="0.05", cur="EUR"), row(2, price="0.05", cur="EUR")))
        self.assertEqual(d["rows"][0]["revenue"], "0.10")  # 0.054 -> 0.05 twice

    def test_r1_conversion_is_case_insensitive_on_currency(self):
        d = self.json_rows(text(row(1, price="100.00", cur="eur")))
        self.assertEqual(d["rows"][0]["revenue"], "108.00")

    # R2: labels and ordering

    def test_r2_regions_group_case_insensitively_with_tidied_first_spelling(self):
        t = text(row(1, region=" north  EAST"), row(2, region="North East"), row(3, region="NORTH   east"))
        data, total = self.body(t)
        self.assertEqual([c[0] for c in data], ["north EAST"])
        self.assertEqual(data[0][1], "3")

    def test_r2_groups_sort_case_insensitively(self):
        data, _ = self.body(text(row(1, region="b"), row(2, region="A"), row(3, region="c")))
        self.assertEqual([c[0] for c in data], ["A", "b", "c"])

    # R3: void rows

    def test_r3_void_rows_vanish(self):
        t = text(row(1, price="10.00"), row(2, region="West", price="99.00", status="void"),
                 row(3, price="5.00", status="VOID"))
        d = self.json_rows(t)
        self.assertEqual([r["group"] for r in d["rows"]], ["East"])
        self.assertEqual((d["rows"][0]["orders"], d["rows"][0]["revenue"]), (1, "10.00"))
        self.assertNotIn("Skipped", self.table(t))

    # R4: the skipped line

    def test_r4_skipped_line_says_rows_even_for_one(self):
        out = self.table(text(row(1), row(2, qty=0)))
        self.assertIn("\n\nSkipped 1 invalid rows\n", out)

    def test_r4_no_skipped_line_when_all_rows_are_fine(self):
        out = self.table(text(row(1)))
        self.assertNotIn("Skipped", out)
        self.assertFalse(out.endswith("\n\n"))

    # R5: json shape

    def test_r5_json_shape(self):
        d = self.json_rows(text(row(1, qty=2, price="10.00"), row(2, qty=3, price="5.50")))
        self.assertEqual(set(d), {"rows", "total"})
        r = d["rows"][0]
        self.assertEqual((r["group"], r["orders"], r["units"], r["revenue"]), ("East", 2, 5, "36.50"))
        self.assertEqual(d["total"]["group"], "TOTAL")
        self.assertIsInstance(r["revenue"], str)

    # R6: table layout

    def test_r6_exact_layout(self):
        out = self.table(text(row(1, qty=2, price="10.00", region="East"),
                              row(2, qty=1, price="5.00", region="West")))
        self.assertEqual(out.splitlines(), [
            "Region  Orders  Units  Revenue  Avg Order   Share",
            "------  ------  -----  -------  ---------  ------",
            "East         1      2    20.00      20.00   80.0%",
            "West         1      1     5.00       5.00   20.0%",
            "------  ------  -----  -------  ---------  ------",
            "TOTAL        2      3    25.00      12.50  100.0%",
        ])

    def test_r6_wide_label_widens_first_column(self):
        out = self.table(text(row(1, region="Northeast")))
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("Region     Orders"))
        self.assertTrue(lines[2].startswith("Northeast       1"))
        self.assertTrue(lines[4].startswith("TOTAL" + " " * 11 + "1"))

    # R7, R8, R9: grouping

    def test_r7_headers(self):
        t = text(row(1))
        self.assertTrue(self.table(t).startswith("Region  "))
        self.assertTrue(self.table(t, "--by", "product").startswith("Product  "))
        self.assertTrue(self.table(t, "--by", "month").startswith("Month    "))

    def test_r8_products_group_like_regions(self):
        t = text(row(1, product=" pen  cap"), row(2, product="Pen Cap"), row(3, product="Ink"))
        data, _ = self.body(t, "--by", "product")
        self.assertEqual([(c[0], c[1]) for c in data], [("Ink", "1"), ("pen cap", "2")])

    def test_r9_month_labels_and_order(self):
        t = text(row(1, date="2024-01-31"), row(2, date="2023-12-01"), row(3, date="2024-01-01"),
                 row(4, date="2024-10-05"))
        data, _ = self.body(t, "--by", "month")
        self.assertEqual([(c[0], c[1]) for c in data],
                         [("2023-12", "1"), ("2024-01", "2"), ("2024-10", "1")])

    # R10, R11: refunds

    def test_r10_refund_subtracts_but_is_not_an_order(self):
        t = text(row(1, qty=5, price="10.00"), row(2, qty=2, price="10.00", status="refunded"))
        d = self.json_rows(t)
        r = d["rows"][0]
        self.assertEqual((r["orders"], r["units"], r["revenue"]), (1, 3, "30.00"))

    def test_r10_refund_is_priced_like_a_paid_row_first(self):
        t = text(row(1, price="100.00", cur="EUR"),
                 row(2, price="10.00", disc="25", qty=2, cur="EUR", status="refunded"))
        d = self.json_rows(t)
        self.assertEqual(d["rows"][0]["revenue"], "91.80")  # 108.00 - 2 * 7.50 * 1.08

    def test_r11_negative_units_are_plain_integers(self):
        t = text(row(1, region="A", qty=1), row(2, region="B", qty=4, status="refunded"))
        data, total = self.body(t)
        self.assertEqual(data[1][:3], ["B", "0", "-4"])
        self.assertEqual(total[2], "-3")

    def test_r11_group_with_only_refunds(self):
        t = text(row(1, region="A"), row(2, region="B", price="3.00", status="refunded"))
        d = self.json_rows(t)
        b = d["rows"][1]
        self.assertEqual((b["orders"], b["units"], b["revenue"], b["avg_order"]), (0, -1, "-3.00", None))

    # R12..R17: columns and number formats

    def test_r12_average_rounds_half_away_from_zero(self):
        t = text(row(1, region="A", price="10.00"), row(2, region="A", price="0.00"),
                 row(3, region="A", price="0.00"), row(4, region="B", price="20.00"),
                 row(5, region="B", price="0.00"), row(6, region="B", price="0.00"),
                 row(7, region="C", price="0.05"), row(8, region="C", price="0.00"))
        data, _ = self.body(t)
        self.assertEqual([c[4] for c in data], ["3.33", "6.67", "0.03"])

    def test_r12_negative_average_rounds_half_away_from_zero(self):
        t = text(row(1, price="0.10"), row(2, price="0.10"), row(3, price="0.25", status="refunded"))
        data, _ = self.body(t)
        self.assertEqual(data[0][3:5], ["(0.05)", "(0.03)"])  # -0.05 revenue, -0.025 average

    def test_r12_dash_when_no_orders(self):
        t = text(row(1, region="A"), row(2, region="B", price="3.00", status="refunded"))
        data, _ = self.body(t)
        self.assertEqual(data[1][3:], ["(3.00)", "-", "-42.9%"])

    def test_r13_share_rounds_half_away_from_zero(self):
        t = text(row(1, region="A", price="6.25"), row(2, region="B", price="93.75"))
        data, _ = self.body(t)
        self.assertEqual([c[5] for c in data], ["6.3%", "93.8%"])

    def test_r13_negative_share_has_a_minus(self):
        t = text(row(1, region="A", price="6.25", status="refunded"), row(2, region="B", price="106.25"))
        data, total = self.body(t)
        self.assertEqual([c[5] for c in data], ["-6.3%", "106.3%"])
        self.assertEqual(total[5], "100.0%")

    def test_r14_zero_total_gives_zero_shares(self):
        t = text(row(1, region="A", price="10.00"), row(2, region="A", price="10.00", status="refunded"))
        data, total = self.body(t)
        self.assertEqual(data[0][5], "0.0%")
        self.assertEqual(total[5], "0.0%")

    def test_r14_empty_report(self):
        out = self.table(text())
        self.assertEqual(out.splitlines()[-1].split(), ["TOTAL", "0", "0", "0.00", "-", "0.0%"])
        self.assertEqual(len(out.splitlines()), 4)

    def test_r15_total_row_average_and_share(self):
        t = text(row(1, region="A", price="10.00"), row(2, region="B", price="20.00"),
                 row(3, region="B", price="30.00"))
        _, total = self.body(t)
        self.assertEqual(total, ["TOTAL", "3", "3", "60.00", "20.00", "100.0%"])

    def test_r16_thousands_separators_and_parentheses(self):
        t = text(row(1, region="A", qty=1000, price="1234.57"),
                 row(2, region="B", price="1234.50", status="refunded"),
                 row(3, region="B", price="1.00"))
        data, total = self.body(t)
        self.assertEqual(data[0][3:5], ["1,234,570.00", "1,234,570.00"])
        self.assertEqual(data[1][3], "(1,233.50)")
        self.assertEqual(total[3], "1,233,336.50")

    def test_r16_negative_amounts_are_right_aligned_in_the_column(self):
        t = text(row(1, region="A", price="3.00", status="refunded"), row(2, region="B", price="1000.00"))
        lines = self.table(t).splitlines()
        col = lines[2].index("(3.00)") + len("(3.00)")
        self.assertEqual(lines[3].index("1,000.00") + len("1,000.00"), col)

    def test_r17_no_negative_zero_share(self):
        t = text(row(1, region="A", price="0.01", status="refunded"), row(2, region="B", price="1000.01"))
        data, _ = self.body(t)
        self.assertEqual(data[0][5], "0.0%")

    def test_r17_no_negative_zero_money(self):
        t = text(row(1, price="0.00"), row(2, price="0.00"), row(3, price="0.00"),
                 row(4, price="0.01", status="refunded"))
        data, _ = self.body(t)
        self.assertEqual(data[0][3:5], ["(0.01)", "0.00"])  # average is -0.0033

    def test_r17_negative_zero_in_csv_and_json(self):
        t = text(row(1, price="0.00"), row(2, price="0.00"), row(3, price="0.00"),
                 row(4, price="0.01", status="refunded"))
        code, out, _ = self.run_cli(t, "--format", "csv")
        self.assertEqual(out.splitlines()[1].split(",")[3:5], ["-0.01", "0.00"])
        d = self.json_rows(t)
        self.assertEqual(d["rows"][0]["avg_order"], "0.00")

    # R18..R22: top N

    def groups(self, **revenues):
        return text(*[row(i, region=name, price=str(rev)) for i, (name, rev) in enumerate(revenues.items(), 1)])

    def test_r18_top_orders_by_revenue_then_label(self):
        t = self.groups(b="10.00", a="10.00", C="20.00")
        data, _ = self.body(t, "--top", "3")
        self.assertEqual([c[0] for c in data], ["C", "a", "b"])

    def test_r18_ties_break_case_sensitively(self):
        t = self.groups(a="10.00", B="10.00")
        data, _ = self.body(t, "--top", "2")
        self.assertEqual([c[0] for c in data], ["B", "a"])

    def test_r18_keeps_n_groups(self):
        t = self.groups(A="50.00", B="30.00", C="15.00", D="5.00")
        data, _ = self.body(t, "--top", "2")
        self.assertEqual([c[0] for c in data], ["A", "B", "Other"])

    def test_r19_other_sums_orders_units_revenue_and_derives_the_rest(self):
        t = text(row(1, region="A", price="50.00"), row(2, region="B", price="30.00"),
                 row(3, region="C", price="15.00", qty=2), row(4, region="D", price="5.00"),
                 row(5, region="D", price="3.00", qty=3))
        data, total = self.body(t, "--top", "2")
        other = data[2]
        self.assertEqual(other, ["Other", "3", "6", "44.00", "14.67", "35.5%"])

    def test_r20_total_and_shares_cover_all_groups(self):
        t = self.groups(A="50.00", B="30.00", C="15.00", D="5.00")
        data, total = self.body(t, "--top", "1")
        self.assertEqual(data[0][5], "50.0%")
        self.assertEqual(data[1][3:], ["50.00", "16.67", "50.0%"])
        self.assertEqual(total[3], "100.00")
        self.assertEqual(total[5], "100.0%")

    def test_r21_top_larger_than_group_count_has_no_other_but_still_sorts(self):
        t = self.groups(A="1.00", B="3.00", C="2.00")
        for n in ("3", "10"):
            data, _ = self.body(t, "--top", n)
            self.assertEqual([c[0] for c in data], ["B", "C", "A"])

    def test_r21_without_top_rows_stay_sorted_by_label(self):
        t = self.groups(A="1.00", B="3.00", C="2.00")
        data, _ = self.body(t)
        self.assertEqual([c[0] for c in data], ["A", "B", "C"])

    def test_r21_top_with_refund_group_sorts_last(self):
        t = text(row(1, region="A", price="1.00"), row(2, region="B", price="5.00", status="refunded"),
                 row(3, region="C", price="2.00"))
        data, _ = self.body(t, "--top", "2")
        self.assertEqual([c[0] for c in data], ["C", "A", "Other"])
        self.assertEqual(data[2][3], "(5.00)")

    def test_r22_bad_top_values(self):
        for bad in ("0", "-1", "abc", "1.5", ""):
            code, out, err = self.run_cli(text(row(1)), "--top", bad)
            self.assertEqual((code, out), (2, ""), bad)
            self.assertEqual(err.strip(), "salesrep: error: --top must be a whole number of at least 1")

    # R23, R24: labels and title

    def test_r23_long_labels_are_shortened_in_the_table_only(self):
        long21 = "A" * 21
        exactly20 = "B" * 20
        t = text(row(1, region=long21), row(2, region=exactly20))
        data, _ = self.body(t)
        self.assertEqual([c[0] for c in data], ["A" * 17 + "...", "B" * 20])
        lines = self.table(t).splitlines()
        self.assertTrue(lines[0].startswith("Region" + " " * 14 + "  Orders"))

    def test_r23_labels_stay_whole_in_csv_and_json(self):
        long21 = "A" * 21
        code, out, _ = self.run_cli(text(row(1, region=long21)), "--format", "csv")
        self.assertEqual(out.splitlines()[1].split(",")[0], long21)
        d = self.json_rows(text(row(1, region=long21)))
        self.assertEqual(d["rows"][0]["group"], long21)

    def test_r23_shortened_other_and_top(self):
        t = text(row(1, region="X" * 30, price="5.00"), row(2, region="Y", price="1.00"))
        data, _ = self.body(t, "--top", "1")
        self.assertEqual(data[0][0], "X" * 17 + "...")
        self.assertEqual(data[1][0], "Other")

    def test_r24_title_is_centered(self):
        t = text(row(1, qty=2, price="10.00", region="East"), row(2, qty=1, price="5.00", region="West"))
        lines = self.table(t, "--title", "Q1").splitlines()
        width = len(lines[2])  # the dashed rule: 6+2+6+2+5+2+7+2+9+2+6 = 49
        self.assertEqual(width, 49)
        self.assertEqual(lines[0], " " * ((49 - 2) // 2) + "Q1")
        self.assertTrue(lines[1].startswith("Region"))

    def test_r24_title_floor_for_odd_padding(self):
        t = text(row(1))
        lines = self.table(t, "--title", "ABCD").splitlines()
        width = len(lines[2])
        self.assertEqual(width, 49)
        self.assertEqual(lines[0], " " * 22 + "ABCD")
        self.assertEqual(lines[0], lines[0].rstrip())

    def test_r24_title_wider_than_the_table(self):
        t = text(row(1))
        title = "A very long report title indeed, wider than this table"
        lines = self.table(t, "--title", title).splitlines()
        self.assertEqual(lines[0], title)

    def test_r24_no_title_by_default(self):
        self.assertTrue(self.table(text(row(1))).startswith("Region"))

    # R25..R28: formats

    def test_r25_format_choices(self):
        t = text(row(1))
        self.assertTrue(self.table(t, "--format", "table").startswith("Region"))
        self.assertTrue(self.table(t, "--format", "csv").startswith("group,orders"))
        self.assertEqual(json.loads(self.table(t, "--format", "json"))["total"]["group"], "TOTAL")
        self.assertEqual(self.table(t, "--json"), self.table(t, "--format", "json"))

    def test_r25_json_with_format_is_an_error(self):
        for fmt in ("table", "csv", "json"):
            code, out, err = self.run_cli(text(row(1)), "--json", "--format", fmt)
            self.assertEqual((code, out), (2, ""))
            self.assertEqual(err.strip(), "salesrep: error: use either --json or --format")

    def test_r26_csv_exact(self):
        t = text(row(1, qty=2, price="1234.50", region="East"),
                 row(2, price="3.00", region="West", status="refunded"),
                 row(3, region='"North, Inc"', price="10.00"),
                 row(4, region='"Say ""hi"""', price="0.00"))
        code, out, err = self.run_cli(t, "--format", "csv")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "group,orders,units,revenue,avg_order,share",
            "East,1,2,2469.00,2469.00,99.7",
            '"North, Inc",1,1,10.00,10.00,0.4',
            '"Say ""hi""",1,1,0.00,0.00,0.0',
            "West,0,-1,-3.00,,-0.1",
            "TOTAL,3,3,2476.00,825.33,100.0",
        ])
        self.assertNotIn("\r", out)

    def test_r26_csv_has_no_title_or_percent_signs(self):
        code, out, _ = self.run_cli(text(row(1)), "--format", "csv", "--title", "X")
        self.assertNotIn("X", out)
        self.assertNotIn("%", out)

    def test_r26_csv_includes_other_row(self):
        t = self.groups(A="50.00", B="30.00", C="20.00")
        code, out, _ = self.run_cli(t, "--format", "csv", "--top", "1")
        self.assertEqual([l.split(",")[0] for l in out.splitlines()], ["group", "A", "Other", "TOTAL"])

    def test_r27_json_new_keys(self):
        t = text(row(1, region="A", price="10.00"), row(2, region="A", price="5.00"),
                 row(3, region="B", price="4.00", status="refunded"))
        d = self.json_rows(t)
        a, b = d["rows"]
        self.assertEqual((a["revenue"], a["avg_order"], a["share"]), ("15.00", "7.50", "136.4"))
        self.assertEqual((b["revenue"], b["avg_order"], b["share"]), ("-4.00", None, "-36.4"))
        self.assertEqual(d["total"], {"group": "TOTAL", "orders": 2, "units": 1, "revenue": "11.00",
                                      "avg_order": "5.50", "share": "100.0"})

    def test_r27_json_rows_follow_table_order(self):
        t = self.groups(A="1.00", B="3.00", C="2.00")
        d = self.json_rows(t, "--top", "2")
        self.assertEqual([r["group"] for r in d["rows"]], ["B", "C", "Other"])

    def test_r28_csv_and_json_send_skipped_rows_to_stderr(self):
        t = text(row(1), row(2, qty=0))
        for args in (("--format", "csv"), ("--json",)):
            code, out, err = self.run_cli(t, *args)
            self.assertNotIn("Skipped", out)
            self.assertEqual(err, "Skipped 1 invalid rows\n  Line 3: qty must be positive\n")

    def test_r28_nothing_on_stderr_without_skips(self):
        code, out, err = self.run_cli(text(row(1)), "--format", "csv")
        self.assertEqual(err, "")

    # R29: skipped rows in detail

    def test_r29_lists_reasons_in_file_order(self):
        t = (HEADER + "\n" + row(1) + "\n\n" + row(2, qty=0) + "\n" + "3,2024-13-45,E,P,1,1,0,USD,paid\n"
             + row(4, cur="XXX") + "\n")
        out = self.table(t)
        self.assertTrue(out.endswith(
            "\n\nSkipped 3 invalid rows\n"
            "  Line 4: qty must be positive\n"
            "  Line 5: bad date '2024-13-45'\n"
            "  Line 6: unknown currency 'XXX'\n"))

    def test_r29_at_most_five_reasons(self):
        t = text(*[row(i, qty=0) for i in range(1, 6)])
        out = self.table(t)
        self.assertEqual(out.splitlines()[-6:], [
            "Skipped 5 invalid rows", "  Line 2: qty must be positive", "  Line 3: qty must be positive",
            "  Line 4: qty must be positive", "  Line 5: qty must be positive",
            "  Line 6: qty must be positive"])

    def test_r29_more_than_five(self):
        t = text(*[row(i, qty=0) for i in range(1, 9)])
        lines = self.table(t).splitlines()
        self.assertEqual(lines[-7], "Skipped 8 invalid rows")
        self.assertEqual(lines[-6], "  Line 2: qty must be positive")
        self.assertEqual(lines[-2], "  Line 6: qty must be positive")
        self.assertEqual(lines[-1], "  ... and 3 more")

    def test_r29_exactly_six(self):
        t = text(*[row(i, qty=0) for i in range(1, 7)])
        self.assertEqual(self.table(t).splitlines()[-1], "  ... and 1 more")

    # R30: duplicate ids

    def test_r30_duplicate_id(self):
        out = self.table(text(row("a", price="1.00"), row("b", price="2.00"), row("a", price="4.00")))
        self.assertIn("  Line 4: duplicate id 'a'", out)
        data, total = self.table_body(out)
        self.assertEqual(total[3], "3.00")

    def table_body(self, out):
        lines = out.splitlines()
        rules = [i for i, l in enumerate(lines) if l and set(l) <= {"-", " "}]
        return ([cells(l) for l in lines[rules[0] + 1: rules[1]]], cells(lines[rules[1] + 1]))

    def test_r30_void_and_refunded_rows_use_up_their_id(self):
        t = text(row("a", status="void"), row("b", status="refunded"), row("a"), row("b"))
        out = self.table(t)
        self.assertIn("  Line 4: duplicate id 'a'", out)
        self.assertIn("  Line 5: duplicate id 'b'", out)

    def test_r30_rejected_rows_do_not_use_up_their_id(self):
        t = text(row("a", qty=0), row("a", price="7.00"))
        out = self.table(t)
        self.assertIn("  Line 2: qty must be positive", out)
        self.assertNotIn("duplicate", out)
        self.assertIn("7.00", out)

    def test_r30_other_rules_win_over_duplicate(self):
        t = text(row("a"), row("a", qty=0))
        self.assertIn("  Line 3: qty must be positive", self.table(t))

    def test_r30_duplicates_are_found_before_the_date_window(self):
        t = text(row("a", date="2023-06-01"), row("a", date="2024-02-01", price="9.00"))
        out = self.table(t, "--from", "2024-01-01")
        self.assertIn("  Line 3: duplicate id 'a'", out)
        self.assertEqual(self.body(t, "--from", "2024-01-01")[0], [])

    def test_r30_ids_are_case_sensitive(self):
        out = self.table(text(row("a"), row("A")))
        self.assertNotIn("duplicate", out)
        self.assertNotIn("Skipped", out)

    # R31: currencies

    def test_r31_cad_and_jpy(self):
        d = self.json_rows(text(row(1, region="A", price="100.00", cur="CAD"),
                                row(2, region="B", price="1000", cur="JPY")))
        self.assertEqual([r["revenue"] for r in d["rows"]], ["74.00", "6.70"])

    def test_r31_jpy_conversion_rounds_per_row(self):
        d = self.json_rows(text(row(1, price="123", cur="JPY", qty=1)))
        self.assertEqual(d["rows"][0]["revenue"], "0.82")  # 0.8241

    def test_r31_jpy_price_must_be_whole(self):
        out = self.table(text(row(1, price="10.50", cur="JPY"), row(2, price="10.00", cur="JPY"),
                              row(3, price="10", cur="JPY")))
        self.assertIn("  Line 2: price must be a whole number for JPY", out)
        self.assertNotIn("Line 3", out)
        self.assertNotIn("Line 4", out)

    def test_r31_rule_order(self):
        t = text(row(1, price="-5", cur="JPY"), row(2, price="10.5", cur="JPY", status="weird"),
                 row(3, price="10.5", cur="JPY", qty=0), row(4, price="10", cur="XXX", status="weird"))
        out = self.table(t)
        self.assertIn("  Line 2: price must not be negative", out)
        self.assertIn("  Line 3: price must be a whole number for JPY", out)
        self.assertIn("  Line 4: qty must be positive", out)
        self.assertIn("  Line 5: unknown currency 'XXX'", out)

    def test_r31_status_rule_still_applies(self):
        out = self.table(text(row(1, status="pending")))
        self.assertIn("  Line 2: unknown status 'pending'", out)

    # R32, R33: date window

    def window_text(self):
        return text(row(1, date="2024-01-31", region="A"), row(2, date="2024-02-01", region="B"),
                    row(3, date="2024-02-29", region="C"), row(4, date="2024-03-01", region="D"))

    def test_r32_from_and_to_are_inclusive(self):
        data, _ = self.body(self.window_text(), "--from", "2024-02-01", "--to", "2024-02-29")
        self.assertEqual([c[0] for c in data], ["B", "C"])

    def test_r32_open_ended_windows(self):
        self.assertEqual([c[0] for c in self.body(self.window_text(), "--from", "2024-02-29")[0]], ["C", "D"])
        self.assertEqual([c[0] for c in self.body(self.window_text(), "--to", "2024-01-31")[0]], ["A"])

    def test_r32_window_applies_to_totals_and_shares(self):
        data, total = self.body(self.window_text(), "--from", "2024-02-01", "--to", "2024-02-29")
        self.assertEqual(total[1], "2")
        self.assertEqual(data[0][5], "50.0%")

    def test_r32_window_works_with_months_and_top(self):
        t = text(row(1, date="2024-01-31", price="1.00"), row(2, date="2024-02-10", price="5.00"),
                 row(3, date="2024-03-10", price="3.00"))
        data, _ = self.body(t, "--by", "month", "--from", "2024-02-01", "--top", "1")
        self.assertEqual([c[0] for c in data], ["2024-02", "Other"])

    def test_r33_rejected_rows_are_listed_whatever_their_date(self):
        t = text(row(1, date="2023-01-01", qty=0), row(2, date="2024-02-01"))
        out = self.table(t, "--from", "2024-01-01")
        self.assertIn("Skipped 1 invalid rows\n  Line 2: qty must be positive", out)

    def test_r33_filtered_out_rows_are_not_reported(self):
        t = text(row(1, date="2023-01-01"))
        out = self.table(t, "--from", "2024-01-01")
        self.assertNotIn("Skipped", out)

    # R34: option errors

    def test_r34_bad_dates(self):
        for opt in ("--from", "--to"):
            for bad in ("2024-02-30", "02/03/2024", "yesterday", "2024-2-3"):
                code, out, err = self.run_cli(text(row(1)), opt, bad)
                self.assertEqual((code, out), (2, ""), (opt, bad))
                self.assertEqual(err.strip(), f"salesrep: error: bad date '{bad}' for {opt}")

    def test_r34_from_after_to(self):
        code, out, err = self.run_cli(text(row(1)), "--from", "2024-03-02", "--to", "2024-03-01")
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err.strip(), "salesrep: error: --from is after --to")

    def test_r34_same_day_window_is_fine(self):
        code, out, _ = self.run_cli(text(row(1, date="2024-03-01")), "--from", "2024-03-01", "--to", "2024-03-01")
        self.assertEqual(code, 0)

    # R35: exit status

    def test_r35_strict(self):
        t = text(row(1), row(2, qty=0))
        code, out, _ = self.run_cli(t, "--strict")
        self.assertEqual(code, 1)
        self.assertIn("Skipped 1 invalid rows", out)
        self.assertEqual(self.run_cli(t)[0], 0)

    def test_r35_strict_without_skips(self):
        self.assertEqual(self.run_cli(text(row(1)), "--strict")[0], 0)
        self.assertEqual(self.run_cli(text(row(1, status="void")), "--strict")[0], 0)

    def test_r35_strict_with_csv(self):
        code, out, err = self.run_cli(text(row(1), row(2, qty=0)), "--strict", "--format", "csv")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("group,orders"))
        self.assertIn("Skipped 1 invalid rows", err)

    def test_r35_missing_column_is_status_two(self):
        code, out, err = self.run_cli("id,date\n1,2024-01-01\n")
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err.strip(), "salesrep: error: missing column 'region'")

    def test_r35_strict_does_not_hide_option_errors(self):
        self.assertEqual(self.run_cli(text(row(1)), "--strict", "--top", "x")[0], 2)

    # Interactions between rules

    def test_x_refund_average_uses_orders_not_rows(self):
        t = text(row(1, price="10.00"), row(2, price="4.00", status="refunded"),
                 row(3, price="8.00"))
        data, _ = self.body(t)
        self.assertEqual(data[0][1:5], ["2", "1", "14.00", "7.00"])

    def test_x_other_row_after_refund_ordering_keeps_total(self):
        t = text(row(1, region="A", price="10.00"), row(2, region="B", price="4.00", status="refunded"),
                 row(3, region="C", price="8.00"))
        data, total = self.body(t, "--top", "1")
        self.assertEqual([c[0] for c in data], ["A", "Other"])
        self.assertEqual(data[1][1:], ["1", "0", "4.00", "4.00", "28.6%"])
        self.assertEqual((total[3], total[5]), ("14.00", "100.0%"))

    def test_x_duplicate_void_then_window(self):
        t = text(row("a", status="void", date="2023-01-01"), row("a", date="2024-02-01"))
        out = self.table(t, "--from", "2024-01-01")
        self.assertIn("duplicate id 'a'", out)

    def test_x_title_width_follows_shortened_labels(self):
        t = text(row(1, region="Z" * 40))
        lines = self.table(t, "--title", "T").splitlines()
        rule_line = lines[2]
        self.assertEqual(lines[0], " " * ((len(rule_line) - 1) // 2) + "T")
        self.assertTrue(lines[3].startswith("Z" * 17 + "..."))

    # Regression: behaviour that must not change

    def test_reg_total_row_and_rule_lines(self):
        lines = self.table(text(row(1, region="A"), row(2, region="B"))).splitlines()
        self.assertEqual(lines[1], lines[-2])
        self.assertTrue(lines[-1].startswith("TOTAL"))

    def test_reg_missing_value_and_bad_values_are_reported(self):
        t = (HEADER + "\n" + "1,2024-01-01,E,P,x,1,0,USD,paid\n" + "2,2024-01-01,E,P,1,abc,0,USD,paid\n"
             + "3,2024-01-01,E,P,1,1,150,USD,paid\n" + ",2024-01-01,E,P,1,1,0,USD,paid\n")
        out = self.table(t)
        self.assertIn("  Line 2: bad quantity 'x'", out)
        self.assertIn("  Line 3: bad price 'abc'", out)
        self.assertIn("  Line 4: discount must be between 0 and 100", out)
        self.assertIn("  Line 5: missing value for 'id'", out)

    def test_reg_defaults_for_optional_columns(self):
        t = "id,date,region,product,qty,unit_price\n1,2024-01-01,E,P,2,2.50\n"
        d = self.json_rows(t)
        self.assertEqual(d["rows"][0]["revenue"], "5.00")

    def test_reg_sum_of_rows_matches_total(self):
        t = text(*[row(i, region=f"R{i % 3}", price=f"{i}.37") for i in range(1, 10)])
        d = self.json_rows(t)
        from decimal import Decimal
        self.assertEqual(sum(Decimal(r["revenue"]) for r in d["rows"]), Decimal(d["total"]["revenue"]))

    def test_reg_long_id_and_label_limits(self):
        t = text(row("x" * 21), row(2, region="R" * 41))
        out = self.table(t)
        self.assertIn("  Line 2: id longer than 20 characters", out)
        self.assertIn("  Line 3: region or product longer than 40 characters", out)


if __name__ == "__main__":
    unittest.main()
