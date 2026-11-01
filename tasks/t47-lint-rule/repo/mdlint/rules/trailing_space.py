from ..registry import register
from ..rule import Rule


@register("trailing-space")
class TrailingSpace(Rule):
    """No spaces or tabs at the end of a line."""

    def check(self, line):
        if line.text != line.text.rstrip():
            self.report(line.number, "trailing whitespace")
