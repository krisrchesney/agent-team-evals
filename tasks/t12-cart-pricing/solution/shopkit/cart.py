"""The shopping cart."""
from .pricing import price


class Cart:
    def __init__(self, tax_bp=0):
        self.tax_bp = tax_bp
        self._lines = []  # [sku, unit_price, qty]
        self._coupons = []

    def _find(self, sku):
        for line in self._lines:
            if line[0] == sku:
                return line
        return None

    def add_item(self, sku, unit_price, qty=1):
        if not isinstance(qty, int) or qty < 1:
            raise ValueError("qty must be an int >= 1")
        line = self._find(sku)
        if line is None:
            self._lines.append([sku, unit_price, qty])
        elif line[1] != unit_price:
            raise ValueError(f"{sku!r} is already in the cart at a different price")
        else:
            line[2] += qty

    def remove_item(self, sku):
        line = self._find(sku)
        if line is None:
            raise KeyError(sku)
        self._lines.remove(line)

    def set_quantity(self, sku, qty):
        if not isinstance(qty, int) or qty < 0:
            raise ValueError("qty must be an int >= 0")
        line = self._find(sku)
        if line is None:
            raise KeyError(sku)
        if qty == 0:
            self._lines.remove(line)
        else:
            line[2] = qty

    def apply_coupon(self, coupon):
        self._coupons.append(coupon)

    def totals(self):
        return price(self._lines, self._coupons, self.tax_bp)
