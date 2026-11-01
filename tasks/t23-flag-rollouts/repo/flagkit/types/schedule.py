from ..decision import Decision
from ..errors import FlagConfigError
from ..flag import Flag, flag_type
from ..timeutil import format_time, parse_time


@flag_type("schedule")
class ScheduleFlag(Flag):
    """On for everyone from `start` until `end`."""

    def __init__(self, start, end, **common):
        super().__init__(**common)
        self.start = start
        self.end = end

    @classmethod
    def from_spec(cls, common, spec):
        key = common["key"]
        start = parse_time(key, "start", spec.get("start"))
        end = parse_time(key, "end", spec.get("end"))
        if end <= start:
            raise FlagConfigError(key, "end", "must be after start")
        return cls(start=start, end=end, **common)

    def type_fields(self):
        return {"start": format_time(self.start), "end": format_time(self.end)}

    def evaluate(self, ctx, now):
        if not self.enabled:
            return Decision(self.key, False, "disabled")
        user = ctx.user_key()
        if user in self.overrides:
            return Decision(self.key, self.overrides[user], "override")
        if self.start <= now < self.end:
            return Decision(self.key, True, "schedule")
        return Decision(self.key, False, "outside_schedule")
