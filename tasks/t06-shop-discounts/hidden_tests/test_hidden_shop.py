import contextlib
import io
import json
import os
import tempfile
import unittest

from shop import Catalog, Item, Line, LineQuote, Order, Quote, price_order
from shop.cli import main
from shop.invoice import render_invoice
from shop.loader import catalog_from_list, order_from_dict, quote_to_dict

CATALOG_ROWS = [
    {"sku": "W", "name": "Widget", "price_cents": 1000},
    {"sku": "B", "name": "Bread", "price_cents": 300, "category": "food"},
    {"sku": "P", "name": "Pen", "price_cents": 150, "bundle": [3, 2]},
    {"sku": "K", "name": "Book", "price_cents": 2000, "category": "books"},
    {"sku": "N", "name": "Gift", "price_cents": 500, "taxable": False},
    {"sku": "O", "name": "Odd", "price_cents": 1005},
    {"sku": "F", "name": "Five", "price_cents": 5},
]


def catalog():
    return catalog_from_list(CATALOG_ROWS)


def order(*pairs, coupons=()):
    return Order(tuple(Line(s, q) for s, q in pairs), coupons=tuple(coupons))


def quote(*pairs, coupons=()):
    return price_order(order(*pairs, coupons=coupons), catalog())


class Cli:
    """Run the CLI on temp files and capture what it prints."""

    def __init__(self, test, order_data):
        self.tmp = tempfile.TemporaryDirectory()
        test.addCleanup(self.tmp.cleanup)
        self.cat = os.path.join(self.tmp.name, "catalog.json")
        self.ord = os.path.join(self.tmp.name, "order.json")
        with open(self.cat, "w", encoding="utf-8") as f:
            json.dump(CATALOG_ROWS, f)
        with open(self.ord, "w", encoding="utf-8") as f:
            json.dump(order_data, f)

    def run(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([self.cat, self.ord, *extra])
        return code, out.getvalue(), err.getvalue()


class HiddenShop(unittest.TestCase):
    # R1: Item.bundle

    def test_r1_bundle_defaults_to_none(self):
        self.assertIsNone(Item("x", "x", 1).bundle)

    def test_r1_valid_bundles(self):
        self.assertEqual(tuple(Item("x", "x", 1, bundle=(3, 2)).bundle), (3, 2))
        self.assertEqual(tuple(Item("x", "x", 1, "food", False, (2, 1)).bundle), (2, 1))

    def test_r1_invalid_bundles_raise_value_error(self):
        for bad in [(2, 2), (3, 0), (1, 1), (3,), (3, 2, 1), ("3", 2), (3.0, 2), (2, -1), 5]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                Item("x", "x", 1, bundle=bad)

    # R2: bundle discount arithmetic

    def test_r2_bundle_discount_amounts(self):
        cases = {1: 0, 2: 0, 3: 150, 4: 150, 6: 300, 7: 300, 9: 450}
        for qty, want in cases.items():
            q = quote(("P", qty))
            self.assertEqual(q.lines[0].bundle_discount_cents, want, qty)
            self.assertEqual(q.lines[0].coupon_discount_cents, 0)

    def test_r2_other_bundle_shape(self):
        cat = Catalog([Item("Z", "Zed", 100, bundle=(4, 1))])
        q = price_order(Order((Line("Z", 9),)), cat)
        self.assertEqual(q.lines[0].bundle_discount_cents, 600)

    def test_r2_no_bundle_no_discount(self):
        self.assertEqual(quote(("W", 9)).lines[0].bundle_discount_cents, 0)

    # R3: model fields and totals

    def test_r3_order_fields(self):
        o = Order((Line("W", 1),), "bob", ("SAVE10",))
        self.assertEqual((o.customer, tuple(o.coupons)), ("bob", ("SAVE10",)))
        self.assertEqual(tuple(Order((Line("W", 1),)).coupons), ())

    def test_r3_line_quote_defaults_and_properties(self):
        lq = LineQuote("a", "a", 1, 10, 10, 1)
        self.assertEqual((lq.bundle_discount_cents, lq.coupon_discount_cents), (0, 0))
        lq = LineQuote("a", "a", 1, 100, 100, 1, 30, 20)
        self.assertEqual((lq.discount_cents, lq.net_cents), (50, 50))

    def test_r3_quote_defaults(self):
        q = Quote((), 0, 0, 0)
        self.assertEqual((q.discount_cents, tuple(q.coupons)), (0, ()))

    def test_r3_totals_with_bundle(self):
        q = quote(("P", 3))
        self.assertEqual(q.subtotal_cents, 450)
        self.assertEqual(q.discount_cents, 150)
        self.assertEqual(q.tax_cents, 25)
        self.assertEqual(q.total_cents, 325)
        self.assertEqual(q.lines[0].net_cents, 300)

    def test_r3_quote_discount_sums_lines(self):
        q = quote(("P", 3), ("W", 1), coupons=["SAVE10"])
        self.assertEqual(q.discount_cents, sum(l.discount_cents for l in q.lines))
        self.assertEqual(q.total_cents, q.subtotal_cents - q.discount_cents + q.tax_cents)

    # R4: tax on net

    def test_r4_tax_on_net_after_coupon(self):
        q = quote(("W", 1), coupons=["SAVE10"])
        self.assertEqual(q.lines[0].net_cents, 900)
        self.assertEqual(q.lines[0].tax_cents, 74)  # 74.25, not 83 from the gross 82.5
        self.assertEqual(q.total_cents, 1000 - 100 + 74)

    def test_r4_tax_rates_and_non_taxable(self):
        q = quote(("K", 1), ("N", 2), ("B", 1), coupons=["SAVE10"])
        by_sku = {l.sku: l for l in q.lines}
        self.assertEqual(by_sku["K"].tax_cents, 90)  # net 1800 at 5%
        self.assertEqual(by_sku["N"].tax_cents, 0)
        self.assertEqual(by_sku["B"].tax_cents, 0)

    def test_r4_tax_rounds_per_line(self):
        q = quote(("P", 3), ("P", 3))
        self.assertEqual([l.tax_cents for l in q.lines], [25, 25])
        self.assertEqual(q.tax_cents, 50)

    # R5: coupon codes

    def test_r5_codes_are_stripped_and_upper_cased(self):
        q = quote(("W", 1), coupons=["  save10 "])
        self.assertEqual([(c.code, c.amount_cents) for c in q.coupons], [("SAVE10", 100)])

    def test_r5_repeated_code_counts_once(self):
        q = quote(("W", 2), coupons=["SAVE10", "save10", " SAVE10"])
        self.assertEqual([(c.code, c.amount_cents) for c in q.coupons], [("SAVE10", 200)])
        self.assertEqual(q.discount_cents, 200)

    def test_r5_unknown_code_raises(self):
        from shop.coupons import UnknownCoupon
        with self.assertRaises(UnknownCoupon) as ctx:
            quote(("W", 1), coupons=["SAVE10", "BOGUS"])
        self.assertIsInstance(ctx.exception, ValueError)

    def test_r5_unknown_code_raises_even_with_no_effect(self):
        from shop.coupons import UnknownCoupon
        with self.assertRaises(UnknownCoupon):
            quote(("B", 1), coupons=["nope"])

    def test_r5_food20_covers_only_food(self):
        q = quote(("W", 1), ("B", 2), coupons=["FOOD20"])
        self.assertEqual([l.coupon_discount_cents for l in q.lines], [0, 120])
        self.assertEqual([(c.code, c.amount_cents) for c in q.coupons], [("FOOD20", 120)])

    def test_r5_fiveoff_threshold_is_inclusive(self):
        q = quote(("W", 5), coupons=["FIVEOFF"])
        self.assertEqual([(c.code, c.amount_cents) for c in q.coupons], [("FIVEOFF", 500)])
        q = quote(("W", 4), ("F", 199), coupons=["FIVEOFF"])  # net 4995
        self.assertEqual(q.coupons, ())
        self.assertEqual(q.discount_cents, 0)

    # R6: order of application and skipping

    def test_r6_order_matters_save10_first(self):
        q = quote(("W", 5), coupons=["SAVE10", "FIVEOFF"])
        self.assertEqual([(c.code, c.amount_cents) for c in q.coupons], [("SAVE10", 500)])
        self.assertEqual(q.discount_cents, 500)

    def test_r6_order_matters_fiveoff_first(self):
        q = quote(("W", 5), coupons=["FIVEOFF", "SAVE10"])
        self.assertEqual([(c.code, c.amount_cents) for c in q.coupons],
                         [("FIVEOFF", 500), ("SAVE10", 450)])
        self.assertEqual(q.discount_cents, 950)

    def test_r6_percent_rounds_half_up(self):
        q = quote(("O", 1), coupons=["SAVE10"])  # 100.5 -> 101
        self.assertEqual(q.coupons[0].amount_cents, 101)
        q = quote(("F", 1), coupons=["SAVE10"])  # 0.5 -> 1
        self.assertEqual(q.coupons[0].amount_cents, 1)

    def test_r6_zero_amount_coupon_is_skipped(self):
        q = quote(("F", 1), coupons=["FOOD20"])  # no food lines
        self.assertEqual(q.coupons, ())
        cat = Catalog([Item("T", "Tiny", 2, category="food")])
        q = price_order(Order((Line("T", 1),), coupons=("FOOD20",)), cat)  # 0.4 -> 0
        self.assertEqual(q.coupons, ())
        self.assertEqual(q.discount_cents, 0)

    def test_r6_sees_bundle_discounted_nets(self):
        q = quote(("P", 3), coupons=["SAVE10"])  # net 300 after the bundle
        self.assertEqual(q.coupons[0].amount_cents, 30)
        self.assertEqual(q.lines[0].coupon_discount_cents, 30)
        self.assertEqual(q.discount_cents, 180)

    def test_r6_fiveoff_checks_net_not_gross(self):
        q = quote(("P", 40), coupons=["FIVEOFF"])  # gross 6000, net 4050
        self.assertEqual(q.coupons, ())
        q = quote(("P", 60), coupons=["FIVEOFF"])  # gross 9000, net 6000
        self.assertEqual([(c.code, c.amount_cents) for c in q.coupons], [("FIVEOFF", 500)])

    # R7: splitting a coupon over lines

    def test_r7_proportional_split_with_largest_remainder(self):
        cat = Catalog([Item("a", "a", 333), Item("b", "b", 333), Item("c", "c", 334)])
        o = Order((Line("a", 1), Line("b", 1), Line("c", 1)), coupons=("SAVE10",))
        q = price_order(o, cat)
        self.assertEqual(q.coupons[0].amount_cents, 100)
        self.assertEqual([l.coupon_discount_cents for l in q.lines], [33, 33, 34])

    def test_r7_ties_go_to_the_earlier_line(self):
        q = quote(("F", 1), ("F", 1), ("F", 1), ("F", 1), coupons=["SAVE10"])  # 2 cents over 4 lines
        self.assertEqual(q.coupons[0].amount_cents, 2)
        self.assertEqual([l.coupon_discount_cents for l in q.lines], [1, 1, 0, 0])

    def test_r7_shares_accumulate_over_coupons(self):
        q = quote(("W", 1), ("B", 2), coupons=["FOOD20", "SAVE10"])
        self.assertEqual([(c.code, c.amount_cents) for c in q.coupons],
                         [("FOOD20", 120), ("SAVE10", 148)])
        self.assertEqual([l.coupon_discount_cents for l in q.lines], [100, 168])

    def test_r7_split_over_eligible_lines_only(self):
        q = quote(("W", 1), ("B", 1), ("B", 2), coupons=["FOOD20"])  # food nets 300 and 600
        self.assertEqual([l.coupon_discount_cents for l in q.lines], [0, 60, 120])

    # R8: invoice

    def test_r8_invoice_without_discount_is_unchanged(self):
        q = quote(("W", 2), ("B", 1))
        self.assertEqual(render_invoice(q), "\n".join([
            "Widget            2 x   10.00     20.00",
            "Bread             1 x    3.00      3.00",
            "Subtotal: 23.00",
            "Tax: 1.65",
            "Total: 24.65",
        ]))

    def test_r8_invoice_with_bundle_and_coupons(self):
        q = quote(("P", 7), ("B", 2), coupons=["FOOD20", "SAVE10"])
        self.assertEqual(render_invoice(q), "\n".join([
            "Pen               7 x    1.50     10.50",
            "Bread             2 x    3.00      6.00",
            "Subtotal: 16.50",
            "  Bundle Pen: -3.00",
            "  Coupon FOOD20: -1.20",
            "  Coupon SAVE10: -1.23",
            "Discount: -5.43",
            "Tax: 0.56",
            "Total: 11.63",
        ]))

    def test_r8_invoice_bundle_only(self):
        q = quote(("P", 3))
        self.assertEqual(render_invoice(q).splitlines()[1:],
                         ["Subtotal: 4.50", "  Bundle Pen: -1.50", "Discount: -1.50",
                          "Tax: 0.25", "Total: 3.25"])

    def test_r8_invoice_lists_bundles_in_line_order(self):
        cat = Catalog([Item("a", "Aa", 100, bundle=(2, 1)), Item("b", "Bb", 100, bundle=(2, 1))])
        q = price_order(Order((Line("b", 2), Line("a", 4))), cat)
        text = render_invoice(q)
        self.assertLess(text.index("  Bundle Bb: -1.00"), text.index("  Bundle Aa: -2.00"))

    # R9: loader

    def test_r9_catalog_bundle_key(self):
        cat = catalog()
        self.assertEqual(tuple(cat.get("P").bundle), (3, 2))
        self.assertIsNone(cat.get("W").bundle)

    def test_r9_order_coupons_key(self):
        o = order_from_dict({"lines": [{"sku": "W", "qty": 1}], "coupons": ["save10"]})
        self.assertEqual(tuple(o.coupons), ("save10",))
        o = order_from_dict({"lines": [{"sku": "W", "qty": 1}], "customer": "amy"})
        self.assertEqual((tuple(o.coupons), o.customer), ((), "amy"))

    def test_r9_quote_dict_new_keys(self):
        d = quote_to_dict(quote(("P", 7), ("B", 2), coupons=["FOOD20", "SAVE10"]))
        self.assertEqual(d["discount_cents"], 543)
        self.assertEqual(d["coupons"], [{"code": "FOOD20", "amount_cents": 120},
                                        {"code": "SAVE10", "amount_cents": 123}])
        pen, bread = d["lines"]
        self.assertEqual((pen["bundle_discount_cents"], pen["coupon_discount_cents"], pen["net_cents"]),
                         (300, 75, 675))
        self.assertEqual((bread["bundle_discount_cents"], bread["coupon_discount_cents"],
                          bread["net_cents"]), (0, 168, 432))
        self.assertEqual((d["subtotal_cents"], d["tax_cents"], d["total_cents"]), (1650, 56, 1163))

    def test_r9_new_keys_present_when_zero(self):
        d = quote_to_dict(quote(("W", 1)))
        self.assertEqual(d["discount_cents"], 0)
        self.assertEqual(d["coupons"], [])
        self.assertEqual(d["lines"][0]["net_cents"], 1000)
        self.assertEqual(d["lines"][0]["bundle_discount_cents"], 0)
        self.assertEqual(d["lines"][0]["coupon_discount_cents"], 0)

    # R10: CLI

    def test_r10_cli_coupon_option(self):
        cli = Cli(self, {"lines": [{"sku": "W", "qty": 1}]})
        code, out, err = cli.run("--coupon", "save10")
        self.assertEqual(code, 0)
        self.assertIn("  Coupon SAVE10: -1.00", out.splitlines())
        self.assertEqual(err, "")

    def test_r10_cli_codes_come_after_the_order_file_codes(self):
        cli = Cli(self, {"lines": [{"sku": "W", "qty": 5}], "coupons": ["FIVEOFF"]})
        code, out, _ = cli.run("--coupon", "SAVE10")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[lines.index("  Coupon FIVEOFF: -5.00") + 1], "  Coupon SAVE10: -4.50")

    def test_r10_cli_json_output(self):
        cli = Cli(self, {"lines": [{"sku": "W", "qty": 1}]})
        code, out, _ = cli.run("--json", "--coupon", "SAVE10", "--coupon", "FIVEOFF")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["discount_cents"], 100)
        self.assertEqual(d["coupons"], [{"code": "SAVE10", "amount_cents": 100}])

    def test_r10_cli_unknown_coupon(self):
        cli = Cli(self, {"lines": [{"sku": "W", "qty": 1}]})
        code, out, err = cli.run("--coupon", " bogus ")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err.strip(), "shop: error: unknown coupon 'BOGUS'")

    def test_r10_cli_unknown_coupon_in_order_file(self):
        cli = Cli(self, {"lines": [{"sku": "W", "qty": 1}], "coupons": ["zzz"]})
        code, out, err = cli.run()
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err.strip(), "shop: error: unknown coupon 'ZZZ'")

    # R11: nothing changes without bundles or coupons

    def test_r11_old_quote_numbers(self):
        q = quote(("W", 2), ("B", 1), ("K", 1), ("N", 3))
        self.assertEqual((q.subtotal_cents, q.tax_cents, q.total_cents), (5800, 165 + 100, 5800 + 265))
        self.assertEqual([l.tax_cents for l in q.lines], [165, 0, 100, 0])
        self.assertEqual(q.discount_cents, 0)

    def test_r11_old_dict_keys_keep_their_values(self):
        d = quote_to_dict(quote(("W", 2), ("B", 1)))
        self.assertEqual(d["lines"][0]["sku"], "W")
        self.assertEqual({k: d["lines"][0][k] for k in
                          ("name", "qty", "unit_cents", "gross_cents", "tax_cents")},
                         {"name": "Widget", "qty": 2, "unit_cents": 1000, "gross_cents": 2000,
                          "tax_cents": 165})
        self.assertEqual((d["subtotal_cents"], d["tax_cents"], d["total_cents"]), (2300, 165, 2465))

    def test_r11_old_constructor_calls_still_work(self):
        lq = LineQuote("W", "Widget", 1, 1000, 1000, 83)
        q = Quote((lq,), 1000, 83, 1083)
        self.assertEqual(q.total_cents, 1083)
        o = Order((Line("W", 1),), "amy")
        self.assertEqual(o.customer, "amy")

    def test_r11_cli_plain_invoice(self):
        cli = Cli(self, {"lines": [{"sku": "W", "qty": 2}, {"sku": "B", "qty": 1}]})
        code, out, err = cli.run()
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[-3:], ["Subtotal: 23.00", "Tax: 1.65", "Total: 24.65"])
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
