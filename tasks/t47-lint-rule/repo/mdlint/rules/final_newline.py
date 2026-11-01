from ..registry import register
from ..rule import Rule


@register("final-newline")
class FinalNewline(Rule):
    """A non-empty document ends with a line break. Reported at its last line."""

    def finish(self, doc):
        if doc.lines and not doc.text.endswith("\n"):
            self.report(doc.lines[-1].number, "no newline at the end of the document")
