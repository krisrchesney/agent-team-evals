from . import types  # noqa: F401  (registers the built-in flag types)
from .clock import SystemClock
from .context import Context
from .errors import FlagConfigError, UnknownFlag
from .flag import FLAG_TYPES, Flag


class FlagClient:
    def __init__(self, flags=(), clock=None):
        self.clock = clock or SystemClock()
        self.flags = {}
        self.exposures = []
        for spec in flags:
            self.add(spec)

    @staticmethod
    def supported_types():
        return sorted(FLAG_TYPES)

    def add(self, spec):
        flag = spec if isinstance(spec, Flag) else Flag.from_dict(spec)
        if flag.key in self.flags:
            raise FlagConfigError(flag.key, "key", "is defined twice")
        self.flags[flag.key] = flag
        return flag

    def evaluate(self, key, ctx=None):
        flag = self.flags.get(key)
        if flag is None:
            raise UnknownFlag(key)
        ctx = ctx or Context()
        now = self.clock.now()
        decision = flag.evaluate(ctx, now)
        self.exposures.append({"flag": key, "on": decision.on, "reason": decision.reason,
                               "user": ctx.user_key()})
        return decision

    def is_on(self, key, ctx=None):
        return self.evaluate(key, ctx).on

    def evaluate_all(self, ctx=None):
        return {key: self.evaluate(key, ctx) for key in sorted(self.flags)}

    def dump(self):
        return [self.flags[key].to_dict() for key in sorted(self.flags)]
