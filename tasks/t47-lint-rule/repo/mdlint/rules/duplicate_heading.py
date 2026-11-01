import re

from ..registry import register
from ..rule import Rule

HEADING = re.compile(r"^#{1,6}\s+(\S.*?)\s*$")


@register("duplicate-heading")
class DuplicateHeading(Rule):
    """The same heading text twice in one document is reported at the second one."""
    PROSE_ONLY = True

    def fresh(self):
        return {"seen": set()}

    def check(self, line):
        match = HEADING.match(line.text)
        if not match:
            return
        title = match.group(1).lower()
        if title in self.state["seen"]:
            self.report(line.number, f"duplicate heading {match.group(1)!r}")
        else:
            self.state["seen"].add(title)
