"""Whole patches against a directory tree. See docs/SPEC.md."""
from collections import namedtuple

FileResult = namedtuple("FileResult", "path action hunks")


def apply_patch_text(patch_text, root, strip=1, max_fuzz=2, dry_run=False, reverse=False):
    raise NotImplementedError


def make_tree_diff(old_tree, new_tree, context=3):
    raise NotImplementedError
