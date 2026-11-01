from dataclasses import dataclass


@dataclass(frozen=True)
class Line:
    number: int     # 1-based
    text: str       # without the line break
    in_code: bool   # True for the lines of a fenced code block, fences included


class Document:
    def __init__(self, text, path="<text>"):
        self.text = text
        self.path = path
        raw = text.split("\n")
        if raw and raw[-1] == "":
            raw.pop()
        self.lines = []
        fenced = False
        for number, content in enumerate(raw, start=1):
            is_fence = content.lstrip().startswith("```")
            if is_fence and not fenced:
                fenced = True
                self.lines.append(Line(number, content, True))
            elif is_fence:
                fenced = False
                self.lines.append(Line(number, content, True))
            else:
                self.lines.append(Line(number, content, fenced))
