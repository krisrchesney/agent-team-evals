"""Applying one FilePatch to a text, with offsets and fuzz. See docs/SPEC.md."""
from collections import namedtuple

from .errors import PatchFailed
from .lines import join_lines, split_lines

HunkResult = namedtuple("HunkResult", "index offset fuzz")
ApplyResult = namedtuple("ApplyResult", "text hunks")


def _context_edges(hunk):
    lead = 0
    for ln in hunk.lines:
        if ln.tag != " ":
            break
        lead += 1
    trail = 0
    for ln in reversed(hunk.lines):
        if ln.tag != " ":
            break
        trail += 1
    return lead, trail


def _find(lines, hunk, fuzz, prev_end, prev_offset):
    lead, trail = _context_edges(hunk)
    drop_lead = min(fuzz, lead)
    drop_trail = min(fuzz, trail, len(hunk.lines) - drop_lead)
    body = hunk.lines[drop_lead:len(hunk.lines) - drop_trail]
    pattern = [ln.text for ln in body if ln.tag in " -"]
    replacement = [ln.text for ln in body if ln.tag in " +"]
    nominal = (hunk.old_start if hunk.old_len == 0 else hunk.old_start - 1) + drop_lead
    base = nominal + prev_offset
    span = len(lines) + abs(base) + 1
    for d in range(span + 1):
        for step in ((0,) if d == 0 else (d, -d)):
            pos = base + step
            if pos < prev_end or pos < 0 or pos + len(pattern) > len(lines):
                continue
            if lines[pos:pos + len(pattern)] == pattern:
                return pos, pattern, replacement, pos - nominal
    return None


def apply_file(text, file_patch, max_fuzz=2):
    lines = split_lines(text)
    out, results, failed = [], [], []
    cursor = 0  # lines before this index are already copied to out
    prev_end, prev_offset = 0, 0
    for index, hunk in enumerate(file_patch.hunks, 1):
        placed = None
        for fuzz in range(max_fuzz + 1):
            found = _find(lines, hunk, fuzz, prev_end, prev_offset)
            if found:
                placed = (found, fuzz)
                break
        if placed is None:
            failed.append(index)
            continue
        (pos, pattern, replacement, offset), fuzz = placed
        out.extend(lines[cursor:pos])
        out.extend(replacement)
        cursor = pos + len(pattern)
        prev_end, prev_offset = cursor, offset
        results.append(HunkResult(index, offset, fuzz))
    if failed:
        raise PatchFailed("hunks failed: %s" % ", ".join(map(str, failed)), failed)
    out.extend(lines[cursor:])
    return ApplyResult(join_lines(out), results)
