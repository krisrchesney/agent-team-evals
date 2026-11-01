"""Exchange rates. A rate is quote major units per one base major unit, e.g. EUR/USD 1.10."""
from decimal import Decimal, InvalidOperation

from . import dates, money
from .errors import InvalidRate, NoRate


class Rates:
    def __init__(self):
        self._rates = {}     # (base, quote) -> {date: Decimal}

    def set(self, base, quote, rate, on):
        money.exponent(base)
        money.exponent(quote)
        if base == quote:
            raise InvalidRate("base and quote must differ", param="quote")
        try:
            value = Decimal(str(rate))
        except InvalidOperation:
            raise InvalidRate(f"not a rate: {rate!r}", param="rate") from None
        if not value.is_finite() or value <= 0:
            raise InvalidRate("rate must be positive", param="rate")
        self._rates.setdefault((base, quote), {})[dates.parse(on, "on")] = value

    def _latest(self, base, quote, on):
        series = self._rates.get((base, quote), {})
        usable = [d for d in series if on is None or d <= on]
        return series[max(usable)] if usable else None

    def get(self, base, quote, on=None):
        """The rate in force on `on` (latest if None): a direct quote, else the inverse of a reverse quote."""
        money.exponent(base)
        money.exponent(quote)
        if base == quote:
            return Decimal(1)
        when = dates.parse(on, "on") if on is not None else None
        direct = self._latest(base, quote, when)
        if direct is not None:
            return direct
        inverse = self._latest(quote, base, when)
        if inverse is not None:
            return Decimal(1) / inverse
        raise NoRate(f"no {base}/{quote} rate" + (f" on or before {when}" if when else ""), param="currency")

    def convert(self, minor, base, quote, on=None):
        """Convert an amount in minor units; the result is rounded half away from zero."""
        if base == quote:
            return minor
        rate = self.get(base, quote, on)
        shift = money.exponent(quote) - money.exponent(base)
        return money.round_half_away(Decimal(minor) * rate * Decimal(10) ** shift)

    def rows(self):
        return [{"base": b, "quote": q, "rate": str(rate), "on": d.isoformat()}
                for (b, q), series in sorted(self._rates.items()) for d, rate in sorted(series.items())]
