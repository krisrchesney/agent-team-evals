"""Coupons: a percentage off, or a fixed number of cents off."""
from .money import BP_SCALE


class Coupon:
    def __init__(self, kind, value):
        if kind not in ("percent", "fixed"):
            raise ValueError(f"unknown coupon kind {kind!r}")
        if not isinstance(value, int) or value <= 0:
            raise ValueError("coupon value must be a positive int")
        if kind == "percent" and value > BP_SCALE:
            raise ValueError("a percent coupon cannot exceed 10000 bp")
        self.kind = kind
        self.value = value

    @classmethod
    def percent(cls, bp):
        return cls("percent", bp)

    @classmethod
    def fixed(cls, cents):
        return cls("fixed", cents)

    def apply(self, amount):
        """The amount left after this coupon."""
        if self.kind == "percent":
            return amount * (BP_SCALE - self.value) // BP_SCALE
        return max(amount - self.value, 0)

    def __repr__(self):
        return f"Coupon({self.kind!r}, {self.value})"
