"""The plan catalog."""
from dataclasses import dataclass

from .errors import Conflict, NotFound, ValidationError

INTERVALS = ("month", "year")


@dataclass
class Plan:
    id: str
    name: str
    interval: str
    price_cents: int
    included_units: int = 0


class Catalog:
    def __init__(self):
        self._plans = {}

    def add(self, plan_id, name, interval, price_cents, included_units=0):
        if plan_id in self._plans:
            raise Conflict(f"plan {plan_id!r} already exists", field="id")
        if interval not in INTERVALS:
            raise ValidationError("interval must be month or year", field="interval")
        if not isinstance(price_cents, int) or price_cents < 0:
            raise ValidationError("price_cents must be a non-negative whole number", field="price_cents")
        plan = Plan(plan_id, name, interval, price_cents, included_units)
        self._plans[plan_id] = plan
        return plan

    def get(self, plan_id):
        try:
            return self._plans[plan_id]
        except KeyError:
            raise NotFound(f"no plan {plan_id!r}", field="plan") from None

    def all(self):
        return sorted(self._plans.values(), key=lambda p: p.id)

    def monthly(self):
        return [p for p in self.all() if p.interval == "month"]

    def yearly(self):
        return [p for p in self.all() if p.interval == "year"]
