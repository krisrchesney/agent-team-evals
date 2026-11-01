"""Generating unified diffs. See docs/SPEC.md."""
import difflib

from .lines import split_lines

NO_NEWLINE = "\\ No newline at end of file\n"


def _range(start, stop):
    length = stop - start
    if length == 1:
        return str(start + 1)
    if length == 0:
        return "%d,0" % start
    return "%d,%d" % (start + 1, length)


def _emit(tag, text):
    if text.endswith("\n"):
        return tag + text
    return tag + text + "\n" + NO_NEWLINE


def make_diff(old, new, old_name="a", new_name="b", context=3):
    if old == new:
        return ""
    a, b = split_lines(old), split_lines(new)
    out = ["--- %s\n" % old_name, "+++ %s\n" % new_name]
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for group in matcher.get_grouped_opcodes(context):
        first, last = group[0], group[-1]
        out.append("@@ -%s +%s @@\n" % (_range(first[1], last[2]), _range(first[3], last[4])))
        for op, i1, i2, j1, j2 in group:
            if op == "equal":
                out.extend(_emit(" ", ln) for ln in a[i1:i2])
                continue
            if op in ("replace", "delete"):
                out.extend(_emit("-", ln) for ln in a[i1:i2])
            if op in ("replace", "insert"):
                out.extend(_emit("+", ln) for ln in b[j1:j2])
    return "".join(out)
