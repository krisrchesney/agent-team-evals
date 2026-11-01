from ..decision import Decision
from ..errors import FlagConfigError
from ..flag import Flag, flag_type
from ..hashing import bucket


@flag_type("rollout")
class RolloutFlag(Flag):
    """On for a fixed share of users. A user's bucket never changes, so raising the percentage only adds users."""

    def __init__(self, percent=0, **common):
        super().__init__(**common)
        self.percent = percent

    @classmethod
    def from_spec(cls, common, spec):
        percent = spec.get("percent", 0)
        if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not 0 <= percent <= 100:
            raise FlagConfigError(common["key"], "percent", "must be a number from 0 to 100")
        return cls(percent=percent, **common)

    def type_fields(self):
        return {"percent": self.percent}

    def evaluate(self, ctx, now):
        if not self.enabled:
            return Decision(self.key, False, "disabled")
        user = ctx.user_key()
        if user is None:
            return Decision(self.key, False, "anonymous")
        if user in self.overrides:
            return Decision(self.key, self.overrides[user], "override")
        if bucket(self.salt, user) < int(self.percent * 100):
            return Decision(self.key, True, "rollout")
        return Decision(self.key, False, "outside_rollout")
