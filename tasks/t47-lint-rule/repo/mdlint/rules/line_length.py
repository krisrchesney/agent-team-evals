from ..errors import ConfigError
from ..registry import register
from ..rule import Rule


@register("line-length")
class LineLength(Rule):
    """No line longer than `max` characters. Code blocks are included."""
    OPTIONS = ("max",)
    REQUIRED = ("max",)

    def configure(self, options):
        limit = options["max"]
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ConfigError(self.name, "max must be a whole number of at least 1")
        self.max = limit

    def check(self, line):
        if len(line.text) > self.max:
            self.report(line.number, f"line is {len(line.text)} characters, the limit is {self.max}")
