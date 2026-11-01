from ..errors import ConfigError
from ..registry import register
from ..stage import Stage

CASTS = {"int": int, "float": float, "str": str}


@register("map")
class Map(Stage):
    """Rename fields, set constant fields and cast field types."""
    OPTIONS = ("rename", "set", "cast")

    def configure(self, options):
        self.rename = options.get("rename", {})
        self.set = options.get("set", {})
        self.cast = options.get("cast", {})
        for opt in ("rename", "set", "cast"):
            if not isinstance(getattr(self, opt), dict):
                raise ConfigError(self.name, f"{opt} must be a dict")
        for field, kind in self.cast.items():
            if kind not in CASTS:
                raise ConfigError(self.name, f"cast {field!r}: type must be one of {', '.join(CASTS)}")

    def process(self, record):
        out = dict(record)
        for field, kind in self.cast.items():
            value = self.need(record, field)
            try:
                out[field] = CASTS[kind](value)
            except (TypeError, ValueError):
                self.reject(record, f"{field!r} cannot be cast to {kind}")
        for old, new in self.rename.items():
            self.need(record, old)
            out[new] = out.pop(old)
        out.update(self.set)
        return [out]
