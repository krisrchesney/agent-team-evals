"""Whole patches against a directory tree. See docs/SPEC.md."""
import os
from collections import namedtuple

from .apply import apply_file
from .diff import make_diff
from .errors import DuplicateTarget, FileExists, MissingFile, PatchFailed, UnsafePath
from .parse import parse

FileResult = namedtuple("FileResult", "path action hunks")
DEV_NULL = "/dev/null"


def _strip(name, strip):
    rest = name.split("/")[strip:]
    stripped = "/".join(rest)
    if not rest or stripped.startswith("/") or ".." in rest:
        raise UnsafePath(name)
    return stripped


def _read(path):
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")


def apply_patch_text(patch_text, root, strip=1, max_fuzz=2, dry_run=False, reverse=False):
    patches = parse(patch_text)
    if reverse:
        patches = [p.reversed() for p in patches]
    plan, seen = [], set()
    for fp in patches:
        if fp.old_name == DEV_NULL:
            action, name = "create", fp.new_name
        elif fp.new_name == DEV_NULL:
            action, name = "delete", fp.old_name
        else:
            action, name = "modify", fp.new_name
        path = _strip(name, strip)
        if path in seen:
            raise DuplicateTarget(path)
        seen.add(path)
        full = os.path.join(root, *path.split("/"))
        if action == "create":
            if os.path.exists(full):
                raise FileExists(path)
            old_text = ""
        else:
            if not os.path.isfile(full):
                raise MissingFile(path)
            old_text = _read(full)
        try:
            result = apply_file(old_text, fp, max_fuzz)
        except PatchFailed as exc:
            exc.path = path
            raise
        plan.append((full, FileResult(path, action, result.hunks), result.text))
    if not dry_run:
        for full, res, text in plan:
            if res.action == "delete":
                os.remove(full)
            else:
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "wb") as fh:
                    fh.write(text.encode("utf-8"))
    return [res for _, res, _ in plan]


def make_tree_diff(old_tree, new_tree, context=3):
    out = []
    for path in sorted(set(old_tree) | set(new_tree)):
        old, new = old_tree.get(path), new_tree.get(path)
        if old == new:
            continue
        if old is None:
            head = ("--- /dev/null\n+++ b/%s\n" % path)
            out.append(make_diff("", new, DEV_NULL, "b/" + path) or head)
        elif new is None:
            head = ("--- a/%s\n+++ /dev/null\n" % path)
            out.append(make_diff(old, "", "a/" + path, DEV_NULL) or head)
        else:
            out.append(make_diff(old, new, "a/" + path, "b/" + path, context))
    return "".join(out)
