import re

from ..registry import register
from ..rule import Rule

HEADING = re.compile(r"^(#{1,6})\s+\S")


@register("heading-increment")
class HeadingIncrement(Rule):
    """A heading may be at most one level deeper than the one before it."""
    PROSE_ONLY = True

    def fresh(self):
        return {"level": 0}

    def check(self, line):
        match = HEADING.match(line.text)
        if not match:
            return
        level = len(match.group(1))
        if level > self.state["level"] + 1:
            self.report(line.number, f"heading jumps from level {self.state['level']} to {level}")
        self.state["level"] = level
