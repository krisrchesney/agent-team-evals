"""Applying one FilePatch to a text, with offsets and fuzz. See docs/SPEC.md."""
from collections import namedtuple

HunkResult = namedtuple("HunkResult", "index offset fuzz")
ApplyResult = namedtuple("ApplyResult", "text hunks")


def apply_file(text, file_patch, max_fuzz=2):
    raise NotImplementedError
