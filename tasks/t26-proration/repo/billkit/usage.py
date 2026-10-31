"""Metered usage records and overage pricing."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from . import periods, quotas
from .errors import ValidationError


@dataclass
class UsageRecord:
    subscription: str
    on: date
    units: int


class UsageLog:
    def __init__(self):
        self.records = []

    def record(self, sub_id, on, units):
        if not isinstance(units, int) or units < 0:
            raise ValidationError("units must be a non-negative whole number", field="units")
        self.records.append(UsageRecord(sub_id, on, units))

    def used_in(self, app, sub_id, on):
        sub = app.subscriptions.get(sub_id)
        plan = app.catalog.get(sub.plan)
        start, end = periods.period_for(sub, on, plan.interval)
        return sum(r.units for r in self.records if r.subscription == sub_id and start <= r.on < end)

    def daily_totals(self, sub_id):
        out = defaultdict(int)
        for r in self.records:
            if r.subscription == sub_id:
                out[r.on] += r.units
        return dict(sorted(out.items()))


def overage_cents(app, log, sub_id, on, unit_price_cents):
    used = log.used_in(app, sub_id, on)
    return quotas.overage_units(app, sub_id, on, used) * unit_price_cents
