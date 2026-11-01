from ..decision import Decision
from ..errors import FlagConfigError
from ..flag import Flag, flag_type
from ..hashing import bucket
from ..timeutil import format_time, parse_time


@flag_type("ramp")
class RampFlag(Flag):
    """A rollout whose percentage follows `steps`: the latest step that has started sets it."""

    def __init__(self, steps, **common):
        super().__init__(**common)
        self.steps = list(steps)  # (start time, percent), in the order they were given

    @classmethod
    def from_spec(cls, common, spec):
        key = common["key"]
        raw = spec.get("steps")
        if not isinstance(raw, list) or not raw:
            raise FlagConfigError(key, "steps", "must be a non-empty list")
        steps = []
        seen = set()
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                raise FlagConfigError(key, f"steps.{i}", "must be a dict with at and percent")
            at = parse_time(key, f"steps.{i}.at", item.get("at"))
            percent = item.get("percent")
            if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not 0 <= percent <= 100:
                raise FlagConfigError(key, f"steps.{i}.percent", "must be a number from 0 to 100")
            if at in seen:
                raise FlagConfigError(key, "steps", f"two steps start at {format_time(at)}")
            seen.add(at)
            steps.append((at, percent))
        return cls(steps=steps, **common)

    def type_fields(self):
        return {"steps": [{"at": format_time(at), "percent": percent} for at, percent in self.steps]}

    def current_percent(self, now):
        started = [step for step in self.steps if step[0] <= now]
        if not started:
            return None
        return max(started, key=lambda step: step[0])[1]

    def evaluate(self, ctx, now):
        if not self.enabled:
            return Decision(self.key, False, "disabled")
        user = ctx.user_key()
        if user is None:
            return Decision(self.key, False, "anonymous")
        if user in self.overrides:
            return Decision(self.key, self.overrides[user], "override")
        percent = self.current_percent(now)
        if percent is not None and bucket(self.salt, user) < int(percent * 100):
            return Decision(self.key, True, "ramp")
        return Decision(self.key, False, "outside_ramp")
