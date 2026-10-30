import unittest

from shopkit import Cart, Coupon


class TestCart(unittest.TestCase):
    def test_simple_total_with_shipping(self):
        c = Cart()
        c.add_item("pen", 150, 2)
        t = c.totals()
        self.assertEqual(t["subtotal"], 300)
        self.assertEqual(t["shipping"], 700)
        self.assertEqual(t["total"], 1000)

    def test_fixed_coupon(self):
        c = Cart()
        c.add_item("book", 2000)
        c.apply_coupon(Coupon.fixed(500))
        self.assertEqual(c.totals()["coupon_discount"], 500)

    def test_bad_quantity(self):
        with self.assertRaises(ValueError):
            Cart().add_item("pen", 100, 0)


if __name__ == "__main__":
    unittest.main()
