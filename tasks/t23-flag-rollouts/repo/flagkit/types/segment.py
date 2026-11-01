from ..decision import Decision
from ..errors import FlagConfigError
from ..flag import Flag, flag_type
from ..hashing import bucket


@flag_type("segment")
class SegmentFlag(Flag):
    """On for users whose attribute `attr` is one of `values`, optionally only for a share of them."""

    def __init__(self, attr, values, percent=100, **common):
        super().__init__(**common)
        self.attr = attr
        self.values = list(values)
        self.percent = percent

    @classmethod
    def from_spec(cls, common, spec):
        key = common["key"]
        attr = spec.get("attr")
        if not isinstance(attr, str) or not attr:
            raise FlagConfigError(key, "attr", "must be a non-empty string")
        values = spec.get("values")
        if not isinstance(values, list) or not values:
            raise FlagConfigError(key, "values", "must be a non-empty list")
        percent = spec.get("percent", 100)
        if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not 0 <= percent <= 100:
            raise FlagConfigError(key, "percent", "must be a number from 0 to 100")
        return cls(attr=attr, values=values, percent=percent, **common)

    def type_fields(self):
        return {"attr": self.attr, "values": list(self.values), "percent": self.percent}

    def evaluate(self, ctx, now):
        if not self.enabled:
            return Decision(self.key, False, "disabled")
        user = ctx.user_key()
        if user is None:
            return Decision(self.key, False, "anonymous")
        if user in self.overrides:
            return Decision(self.key, self.overrides[user], "override")
        if ctx.attrs.get(self.attr) not in self.values:
            return Decision(self.key, False, "outside_segment")
        if bucket(self.salt, user) < int(self.percent * 100):
            return Decision(self.key, True, "segment")
        return Decision(self.key, False, "outside_segment")
