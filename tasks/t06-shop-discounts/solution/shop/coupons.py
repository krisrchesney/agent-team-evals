"""Coupon rules and how a coupon's amount is spread over order lines."""
from dataclasses import dataclass

from .tax import round_half_up_div


class UnknownCoupon(ValueError):
    pass


@dataclass(frozen=True)
class AppliedCoupon:
    code: str
    amount_cents: int


COUPONS = {
    "SAVE10": {"percent": 10},
    "FOOD20": {"percent": 20, "category": "food"},
    "FIVEOFF": {"cents": 500, "min_net": 5000},
}


def normalise(codes):
    """Strip and upper-case codes, drop repeats (first wins), reject unknown ones."""
    seen = []
    for raw in codes:
        code = raw.strip().upper()
        if code not in COUPONS:
            raise UnknownCoupon(code)
        if code not in seen:
            seen.append(code)
    return seen


def split_amount(amount, nets):
    """Split `amount` over `nets` in proportion, largest remainder first, ties to the earlier index."""
    total = sum(nets)
    shares = [amount * n // total for n in nets]
    left = amount - sum(shares)
    order = sorted(range(len(nets)), key=lambda i: (-(amount * nets[i] % total), i))
    for i in order[:left]:
        shares[i] += 1
    return shares


def apply_coupons(codes, nets, categories):
    """Return (per-line discount cents, [AppliedCoupon]) given each line's net after bundles."""
    nets = list(nets)
    discounts = [0] * len(nets)
    applied = []
    for code in normalise(codes):
        rule = COUPONS[code]
        if sum(nets) < rule.get("min_net", 0):
            continue
        eligible = [i for i, n in enumerate(nets)
                    if n > 0 and rule.get("category", categories[i]) == categories[i]]
        eligible_net = sum(nets[i] for i in eligible)
        if "percent" in rule:
            amount = round_half_up_div(eligible_net * rule["percent"], 100)
        else:
            amount = min(rule["cents"], eligible_net)
        if amount <= 0:
            continue
        for i, share in zip(eligible, split_amount(amount, [nets[i] for i in eligible])):
            nets[i] -= share
            discounts[i] += share
        applied.append(AppliedCoupon(code, amount))
    return discounts, applied
