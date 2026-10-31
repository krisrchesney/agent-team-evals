from dataclasses import dataclass, field
from typing import List

SWAP = {" ": " ", "-": "+", "+": "-"}


@dataclass
class Line:
    tag: str  # " " context, "-" removed, "+" added
    text: str  # the line's text with its "\n"; no "\n" means "no newline at end of file"


@dataclass
class Hunk:
    old_start: int
    old_len: int
    new_start: int
    new_len: int
    lines: List[Line] = field(default_factory=list)

    def reversed(self):
        return Hunk(self.new_start, self.new_len, self.old_start, self.old_len,
                    [Line(SWAP[ln.tag], ln.text) for ln in self.lines])


@dataclass
class FilePatch:
    old_name: str
    new_name: str
    hunks: List[Hunk] = field(default_factory=list)

    def reversed(self):
        return FilePatch(self.new_name, self.old_name, [h.reversed() for h in self.hunks])
