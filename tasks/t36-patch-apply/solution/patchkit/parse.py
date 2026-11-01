"""Parsing unified diffs into FilePatch objects. See docs/SPEC.md."""
import re

from .errors import ParseError
from .models import FilePatch, Hunk, Line

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _name(rest):
    return rest.split("\t")[0]


def parse(patch_text):
    lines = patch_text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    n = len(lines)
    patches, current, i = [], None, 0
    while i < n:
        ln = lines[i]
        if ln.startswith("--- "):
            if i + 1 >= n or not lines[i + 1].startswith("+++ "):
                raise ParseError("'--- ' line without '+++ ' line", i + 1)
            current = FilePatch(_name(ln[4:]), _name(lines[i + 1][4:]), [])
            patches.append(current)
            i += 2
        elif ln.startswith("@@"):
            if current is None:
                raise ParseError("hunk before any file header", i + 1)
            hunk, i = _hunk(lines, i)
            current.hunks.append(hunk)
        else:
            i += 1
    return patches


def _hunk(lines, i):
    m = HUNK_RE.match(lines[i])
    if not m:
        raise ParseError("malformed hunk header", i + 1)
    old_start, old_len, new_start, new_len = (int(g) if g is not None else 1 for g in m.groups())
    if m.group(2) is None:
        old_len = 1
    if m.group(4) is None:
        new_len = 1
    hunk = Hunk(old_start, old_len, new_start, new_len, [])
    n = len(lines)
    old_seen = new_seen = 0
    i += 1
    while old_seen < old_len or new_seen < new_len:
        if i >= n:
            raise ParseError("hunk ends before its line counts are used up", n)
        ln = lines[i]
        tag = ln[:1]
        if tag == "\\":
            if not hunk.lines:
                raise ParseError("'\\' line at the start of a hunk", i + 1)
            _no_newline(hunk)
            i += 1
            continue
        if ln == "":
            tag, text = " ", ""
        elif tag in (" ", "-", "+"):
            text = ln[1:]
        else:
            raise ParseError("unexpected line in hunk body", i + 1)
        if tag in (" ", "-"):
            if old_seen >= old_len:
                raise ParseError("hunk has more old lines than its header says", i + 1)
            old_seen += 1
        if tag in (" ", "+"):
            if new_seen >= new_len:
                raise ParseError("hunk has more new lines than its header says", i + 1)
            new_seen += 1
        hunk.lines.append(Line(tag, text + "\n"))
        i += 1
    if i < n and lines[i].startswith("\\"):
        _no_newline(hunk)
        i += 1
    return hunk, i


def _no_newline(hunk):
    last = hunk.lines[-1]
    if last.text.endswith("\n"):
        last.text = last.text[:-1]
