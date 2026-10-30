"""The shopping cart."""
from .pricing import price


class Cart:
    def __init__(self, tax_bp=0):
        self.tax_bp = tax_bp
        self._lines = []  # [sku, unit_price, qty]
        self._coupons = []
        self._totals = None  # cached result of totals()

    def add_item(self, sku, unit_price, qty=1):
        if not isinstance(qty, int) or qty < 1:
            raise ValueError("qty must be an int >= 1")
        self._lines.append([sku, unit_price, qty])
        self._totals = None

    def remove_item(self, sku):
        kept = [line for line in self._lines if line[0] != sku]
        if len(kept) == len(self._lines):
            raise KeyError(sku)
        self._lines = kept

    def set_quantity(self, sku, qty):
        if not isinstance(qty, int) or qty < 0:
            raise ValueError("qty must be an int >= 0")
        for line in self._lines:
            if line[0] == sku:
                if qty == 0:
                    self._lines.remove(line)
                else:
                    line[2] = qty
                self._totals = None
                return
        raise KeyError(sku)

    def apply_coupon(self, coupon):
        self._coupons.append(coupon)

    def totals(self):
        if self._totals is None:
            self._totals = price(self._lines, self._coupons, self.tax_bp)
        return dict(self._totals)
