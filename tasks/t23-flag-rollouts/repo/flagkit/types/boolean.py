from ..decision import Decision
from ..errors import FlagConfigError
from ..flag import Flag, flag_type


@flag_type("boolean")
class BooleanFlag(Flag):
    def __init__(self, value=False, **common):
        super().__init__(**common)
        self.value = value

    @classmethod
    def from_spec(cls, common, spec):
        value = spec.get("value", False)
        if not isinstance(value, bool):
            raise FlagConfigError(common["key"], "value", "must be true or false")
        return cls(value=value, **common)

    def type_fields(self):
        return {"value": self.value}

    def evaluate(self, ctx, now):
        if not self.enabled:
            return Decision(self.key, False, "disabled")
        return Decision(self.key, self.value, "static")
