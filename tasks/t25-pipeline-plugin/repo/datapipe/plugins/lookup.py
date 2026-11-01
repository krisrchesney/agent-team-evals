from ..errors import ConfigError
from ..registry import register
from ..stage import Stage


@register("lookup")
class Lookup(Stage):
    """Add `into` from a fixed table, keyed by the value of `field`."""
    OPTIONS = ("field", "into", "table", "default")
    REQUIRED = ("field", "into", "table")

    def configure(self, options):
        for opt in ("field", "into"):
            if not isinstance(options[opt], str) or not options[opt]:
                raise ConfigError(self.name, f"{opt} must be a non-empty string")
        if not isinstance(options["table"], dict):
            raise ConfigError(self.name, "table must be a dict")
        self.field, self.into, self.table = options["field"], options["into"], options["table"]
        self.has_default = "default" in options
        self.default = options.get("default")

    def process(self, record):
        key = self.need(record, self.field)
        if not isinstance(key, str) or key not in self.table:
            if not self.has_default:
                self.reject(record, f"no entry for {key!r}")
            found = self.default
        else:
            found = self.table[key]
        out = dict(record)
        out[self.into] = found
        return [out]
