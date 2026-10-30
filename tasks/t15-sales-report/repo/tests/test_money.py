import unittest
from decimal import Decimal

from salesrep.money import format_money, quantize, to_decimal


class TestMoney(unittest.TestCase):
    def test_quantize_half_up(self):
        self.assertEqual(quantize(Decimal("2.345")), Decimal("2.35"))
        self.assertEqual(quantize(Decimal("2.344")), Decimal("2.34"))

    def test_format_money(self):
        self.assertEqual(format_money(Decimal("1234567.5")), "1,234,567.50")
        self.assertEqual(format_money(Decimal("0")), "0.00")

    def test_to_decimal(self):
        self.assertEqual(to_decimal(".5"), Decimal("0.5"))
        for bad in ("abc", "NaN", "Infinity", ""):
            with self.assertRaises(ValueError):
                to_decimal(bad)


if __name__ == "__main__":
    unittest.main()
