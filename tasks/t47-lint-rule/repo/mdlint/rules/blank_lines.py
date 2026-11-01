from ..errors import ConfigError
from ..registry import register
from ..rule import Rule


@register("blank-lines")
class BlankLines(Rule):
    """No more than `max` blank lines in a row (default 1). Reported at each extra blank line."""
    OPTIONS = ("max",)

    def configure(self, options):
        limit = options.get("max", 1)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ConfigError(self.name, "max must be a whole number of at least 1")
        self.max = limit

    def fresh(self):
        return {"run": 0}

    def check(self, line):
        if line.text.strip():
            self.state["run"] = 0
            return
        self.state["run"] += 1
        if self.state["run"] > self.max:
            self.report(line.number, f"more than {self.max} blank line(s) in a row")
