import re

from ..errors import ConfigError
from ..registry import register
from ..rule import Rule

ITEM = re.compile(r"^(\d+)\. +\S")


@register("list-numbering")
class ListNumbering(Rule):
    """Items of an ordered list are numbered start, start + 1, and so on."""
    OPTIONS = ("start",)
    PROSE_ONLY = True

    def configure(self, options):
        start = options.get("start", 1)
        if isinstance(start, bool) or not isinstance(start, int) or start < 0:
            raise ConfigError(self.name, "start must be a whole number of at least 0")
        self.start = start

    def fresh(self):
        return {"items": 0}

    def check(self, line):
        match = ITEM.match(line.text)
        if match:
            expected = self.start + self.state["items"]
            self.state["items"] += 1
            if int(match.group(1)) != expected:
                self.report(line.number, f"expected {expected}, found {match.group(1)}")
        elif line.text.strip() and not line.text[0].isspace():
            self.state["items"] = 0
