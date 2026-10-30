import unittest

from shop import Catalog, Item, Line, Order, price_order
from shop.invoice import render_invoice


class TestShop(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog([
            Item("W1", "Widget", 350),
            Item("B1", "Bread", 275, category="food"),
        ])

    def test_quote_totals(self):
        q = price_order(Order((Line("W1", 2), Line("B1", 1))), self.catalog)
        self.assertEqual(q.subtotal_cents, 975)
        self.assertEqual(q.tax_cents, 58)
        self.assertEqual(q.total_cents, 1033)

    def test_invoice_ends_with_total(self):
        q = price_order(Order((Line("W1", 1),)), self.catalog)
        self.assertTrue(render_invoice(q).endswith("Total: 3.79"))


if __name__ == "__main__":
    unittest.main()
