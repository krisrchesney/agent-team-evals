"""Hidden grader for t12. Tests are named after the requirement they check. The methods marked
BUG isolate one planted bug each, so partial credit shows which bugs an agent found; the rest
pass on the starting code, except the random model check at the end (all requirements at once)."""
import random
import unittest

from shopkit import FREE_SHIPPING_MIN_CENTS, SHIPPING_CENTS, Cart, Coupon


def cart(tax_bp=0, items=(), coupons=()):
    c = Cart(tax_bp=tax_bp)
    for sku, price, qty in items:
        c.add_item(sku, price, qty)
    for coupon in coupons:
        c.apply_coupon(coupon)
    return c


class HiddenCart(unittest.TestCase):
    # ---- R1 rounding -------------------------------------------------------------------
    def test_R1_half_up_rounding_BUG(self):
        # 10% of 45 is 4.5 -> 5 (a bulk discount); the same for a percent coupon; and 10% tax
        # on 25 is 2.5 -> 3.
        self.assertEqual(cart(items=[("a", 3, 15)]).totals()["bulk_discount"], 5)
        c = cart(items=[("a", 45, 1)], coupons=[Coupon.percent(1000)])
        self.assertEqual(c.totals()["coupon_discount"], 5)
        self.assertEqual(cart(tax_bp=1000, items=[("a", 25, 1)]).totals()["tax"], 3)

    def test_R1_non_halfway_values_round_normally(self):
        self.assertEqual(cart(tax_bp=1000, items=[("a", 24, 1)]).totals()["tax"], 2)   # 2.4
        self.assertEqual(cart(tax_bp=1000, items=[("a", 26, 1)]).totals()["tax"], 3)   # 2.6
        self.assertEqual(cart(tax_bp=725, items=[("a", 1002, 1)]).totals()["tax"], 73)  # 72.6

    def test_R1_values_are_ints(self):
        t = cart(tax_bp=825, items=[("a", 333, 11)], coupons=[Coupon.percent(1234)]).totals()
        for key, value in t.items():
            self.assertIs(type(value), int, key)

    # ---- R2 cart items ------------------------------------------------------------------
    def test_R2_same_sku_merges_into_one_line_BUG(self):
        c = cart(items=[("a", 100, 6)])
        c.add_item("a", 100, 6)
        t = c.totals()
        self.assertEqual(t["subtotal"], 1200)
        self.assertEqual(t["bulk_discount"], 120)  # one line of 12, not two lines of 6
        with self.assertRaises(ValueError):
            c.add_item("a", 101, 1)
        self.assertEqual(c.totals()["subtotal"], 1200)

    def test_R2_add_item_validation(self):
        for bad in (0, -1, 1.5, "2", None):
            with self.subTest(qty=bad):
                with self.assertRaises(ValueError):
                    Cart().add_item("a", 100, bad)
        c = Cart()
        c.add_item("a", 100)
        self.assertEqual(c.totals()["subtotal"], 100)

    def test_R2_remove_item(self):
        c = cart(items=[("a", 100, 2), ("b", 50, 1)])
        c.remove_item("a")
        self.assertEqual(c.totals()["subtotal"], 50)
        with self.assertRaises(KeyError):
            c.remove_item("a")

    def test_R2_set_quantity(self):
        c = cart(items=[("a", 100, 2), ("b", 50, 1)])
        c.set_quantity("a", 5)
        self.assertEqual(c.totals()["subtotal"], 550)
        c.set_quantity("b", 0)
        self.assertEqual(c.totals()["subtotal"], 500)
        with self.assertRaises(ValueError):
            c.set_quantity("a", -1)
        with self.assertRaises(KeyError):
            c.set_quantity("zzz", 1)
        self.assertEqual(c.totals()["subtotal"], 500)

    # ---- R3 bulk discount ------------------------------------------------------------------
    def test_R3_bulk_applies_from_ten_BUG(self):
        self.assertEqual(cart(items=[("a", 100, 10)]).totals()["bulk_discount"], 100)
        self.assertEqual(cart(items=[("a", 100, 9)]).totals()["bulk_discount"], 0)
        self.assertEqual(cart(items=[("a", 100, 11)]).totals()["bulk_discount"], 110)

    def test_R3_bulk_is_per_line(self):
        t = cart(items=[("a", 100, 12), ("b", 100, 6), ("c", 100, 3)]).totals()
        self.assertEqual(t["bulk_discount"], 120)  # only "a" qualifies
        self.assertEqual(t["subtotal"], 2100)

    def test_R3_set_quantity_can_cross_the_threshold(self):
        c = cart(items=[("a", 200, 3)])
        c.set_quantity("a", 12)
        self.assertEqual(c.totals()["bulk_discount"], 240)
        c.set_quantity("a", 4)
        self.assertEqual(c.totals()["bulk_discount"], 0)

    # ---- R4 coupons ---------------------------------------------------------------------------
    def test_R4_coupons_apply_in_the_order_added_BUG(self):
        a = cart(items=[("a", 10000, 1)], coupons=[Coupon.percent(1000), Coupon.fixed(500)])
        self.assertEqual(a.totals()["coupon_discount"], 1500)   # 9000, then 8500
        self.assertEqual(a.totals()["total"], 8500)
        b = cart(items=[("a", 10000, 1)], coupons=[Coupon.fixed(500), Coupon.percent(1000)])
        self.assertEqual(b.totals()["coupon_discount"], 1450)   # 9500, then 8550
        self.assertEqual(b.totals()["total"], 8550)

    def test_R4_percent_coupon_discount_is_rounded_as_in_R1_BUG(self):
        # 10% of 44 is 4.4 -> 4; of 45 is 4.5 -> 5; of 46 is 4.6 -> 5.
        for price, want in ((44, 4), (45, 5), (46, 5)):
            with self.subTest(price=price):
                t = cart(items=[("a", price, 1)], coupons=[Coupon.percent(1000)]).totals()
                self.assertEqual(t["coupon_discount"], want)
                self.assertEqual(t["total"], price - want + SHIPPING_CENTS)

    def test_R4_coupons_act_on_the_amount_after_bulk(self):
        c = cart(items=[("a", 1000, 12)], coupons=[Coupon.percent(5000)])
        t = c.totals()
        self.assertEqual(t["bulk_discount"], 1200)
        self.assertEqual(t["coupon_discount"], 5400)  # half of 10800

    def test_R4_amount_never_below_zero(self):
        c = cart(items=[("a", 500, 1)], coupons=[Coupon.fixed(800), Coupon.percent(1000)])
        t = c.totals()
        self.assertEqual(t["coupon_discount"], 500)
        self.assertEqual(t["total"], SHIPPING_CENTS)

    def test_R4_coupon_validation(self):
        for args in (("percent", 0), ("percent", 10001), ("fixed", -5), ("bogus", 5)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    Coupon(*args)

    # ---- R5 tax -----------------------------------------------------------------------------------
    def test_R5_tax_is_computed_once_on_the_whole_amount(self):
        # 3 lines of 10c at 5%: 30c * 5% = 1.5 -> 2. (Rounding per line would give 3.)
        t = cart(tax_bp=500, items=[("a", 10, 1), ("b", 10, 1), ("c", 10, 1)]).totals()
        self.assertEqual(t["tax"], 2)

    def test_R5_tax_on_amount_after_discounts_and_not_on_shipping(self):
        c = cart(tax_bp=1000, items=[("a", 2000, 1)], coupons=[Coupon.fixed(500)])
        t = c.totals()
        self.assertEqual(t["tax"], 150)               # 10% of 1500
        self.assertEqual(t["shipping"], SHIPPING_CENTS)
        self.assertEqual(t["total"], 1500 + 150 + SHIPPING_CENTS)

    # ---- R6 shipping ---------------------------------------------------------------------------------
    def test_R6_free_shipping_decided_after_coupons_BUG(self):
        c = cart(items=[("a", 6000, 1)], coupons=[Coupon.fixed(1500)])
        t = c.totals()
        self.assertEqual(t["shipping"], SHIPPING_CENTS)   # 4500 left, under the threshold
        self.assertEqual(t["total"], 4500 + SHIPPING_CENTS)
        d = cart(items=[("a", 6000, 1)], coupons=[Coupon.percent(1000)])
        self.assertEqual(d.totals()["shipping"], 0)       # 5400 left

    def test_R6_threshold_is_amount_before_tax_after_bulk(self):
        self.assertEqual(cart(items=[("a", 5000, 1)]).totals()["shipping"], 0)
        self.assertEqual(cart(items=[("a", 4999, 1)]).totals()["shipping"], SHIPPING_CENTS)
        # tax pushes the total over 5000 but the amount before tax is only 4800
        t = cart(tax_bp=1000, items=[("a", 4800, 1)]).totals()
        self.assertEqual(t["shipping"], SHIPPING_CENTS)
        self.assertEqual(t["total"], 4800 + 480 + SHIPPING_CENTS)
        # a bulk discount can take a line under the threshold: 11 x 500 = 5500, minus 550
        self.assertEqual(cart(items=[("a", 500, 11)]).totals()["shipping"], SHIPPING_CENTS)
        self.assertEqual(FREE_SHIPPING_MIN_CENTS, 5000)

    def test_R6_empty_cart_free_but_zero_amount_cart_pays(self):
        self.assertEqual(Cart().totals()["shipping"], 0)
        c = cart(items=[("a", 500, 1)], coupons=[Coupon.fixed(500)])
        self.assertEqual(c.totals()["shipping"], SHIPPING_CENTS)
        self.assertEqual(cart().totals()["total"], 0)

    # ---- R7 totals() ----------------------------------------------------------------------------------
    def test_R7_totals_follow_later_changes_BUG(self):
        c = cart(items=[("a", 1000, 2), ("b", 500, 1)])
        self.assertEqual(c.totals()["subtotal"], 2500)
        c.remove_item("b")
        self.assertEqual(c.totals()["subtotal"], 2000)
        c.apply_coupon(Coupon.fixed(300))
        self.assertEqual(c.totals()["coupon_discount"], 300)
        self.assertEqual(c.totals()["total"], 1700 + SHIPPING_CENTS)
        c.add_item("a", 1000, 1)
        self.assertEqual(c.totals()["subtotal"], 3000)
        c.set_quantity("a", 1)
        self.assertEqual(c.totals()["subtotal"], 1000)

    def test_R7_empty_cart_is_all_zero(self):
        self.assertEqual(Cart(tax_bp=800).totals(),
                         {"subtotal": 0, "bulk_discount": 0, "coupon_discount": 0,
                          "tax": 0, "shipping": 0, "total": 0})
        c = cart(items=[("a", 100, 1)], coupons=[Coupon.percent(500)])
        c.remove_item("a")
        self.assertEqual(c.totals()["total"], 0)

    def test_R7_keys_and_total_identity(self):
        t = cart(tax_bp=700, items=[("a", 999, 12), ("b", 250, 3)],
                 coupons=[Coupon.percent(1500), Coupon.fixed(200)]).totals()
        self.assertEqual(set(t), {"subtotal", "bulk_discount", "coupon_discount",
                                  "tax", "shipping", "total"})
        self.assertEqual(t["total"], t["subtotal"] - t["bulk_discount"]
                         - t["coupon_discount"] + t["tax"] + t["shipping"])

    # ---- everything at once -----------------------------------------------------------------------------
    def test_R1_to_R7_random_carts_match_a_reference_model(self):
        prices = {"a": 3, "b": 45, "c": 129, "d": 520, "e": 1999, "f": 7}

        def pct(amount, bp):
            return (amount * bp + 5000) // 10000

        def model(lines, coupons, tax_bp):
            subtotal = sum(p * q for p, q in lines.values())
            bulk = sum(pct(p * q, 1000) for p, q in lines.values() if q >= 10)
            left = subtotal - bulk
            start = left
            for kind, value in coupons:
                left = left - pct(left, value) if kind == "percent" else max(left - value, 0)
            tax = pct(left, tax_bp)
            shipping = 0 if not lines or left >= 5000 else 700
            return {"subtotal": subtotal, "bulk_discount": bulk, "coupon_discount": start - left,
                    "tax": tax, "shipping": shipping, "total": left + tax + shipping}

        rng = random.Random(12)
        for _ in range(40):
            tax_bp = rng.choice([0, 500, 725, 1000, 825])
            c = Cart(tax_bp=tax_bp)
            lines, coupons = {}, []
            for step in range(25):
                op = rng.choice(["add", "add", "remove", "set", "coupon"])
                sku = rng.choice(sorted(prices))
                if op == "add":
                    qty = rng.randint(1, 8)
                    c.add_item(sku, prices[sku], qty)
                    lines[sku] = (prices[sku], lines.get(sku, (0, 0))[1] + qty)
                elif op == "remove" and sku in lines:
                    c.remove_item(sku)
                    del lines[sku]
                elif op == "set" and sku in lines:
                    qty = rng.randint(0, 14)
                    c.set_quantity(sku, qty)
                    if qty:
                        lines[sku] = (prices[sku], qty)
                    else:
                        del lines[sku]
                elif op == "coupon":
                    if rng.random() < 0.5:
                        value = rng.choice([250, 500, 1000, 1500])
                        c.apply_coupon(Coupon.percent(value))
                        coupons.append(("percent", value))
                    else:
                        value = rng.choice([50, 300, 1000, 4000])
                        c.apply_coupon(Coupon.fixed(value))
                        coupons.append(("fixed", value))
                self.assertEqual(c.totals(), model(lines, coupons, tax_bp), (tax_bp, op, step))


if __name__ == "__main__":
    unittest.main()
