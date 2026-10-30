"""Grade a finished worktree by running the task's hidden tests in it.

Hidden tests are copied in only after every agent stage has finished, into `_ate_hidden/`,
and run with the stdlib unittest runner. Pass = every hidden test passes.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

HIDDEN_DIR = "_ate_hidden"
_RAN = re.compile(r"^Ran (\d+) tests? in", re.M)
_FAILED = re.compile(r"^FAILED \((.*)\)", re.M)


def clear_bytecode(root):
    """Drop cached .pyc files: a same-size edit within the same second would otherwise run stale code."""
    for cache in Path(root).rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def run_unittest(cwd, start_dir, timeout_s):
    clear_bytecode(cwd)
    cmd = [sys.executable, "-B", "-m", "unittest", "discover", "-s", start_dir, "-t", "."]
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"total": 0, "passed": 0, "failed": 0, "errors": 0, "ok": False,
                "timed_out": True, "output_tail": f"timed out after {timeout_s}s"}
    return parse_unittest_output(proc.stderr + proc.stdout, proc.returncode)


def parse_unittest_output(text, returncode):
    ran = _RAN.search(text)
    total = int(ran.group(1)) if ran else 0
    failed = errors = 0
    m = _FAILED.search(text)
    if m:
        for part in m.group(1).split(","):
            key, _, val = part.strip().partition("=")
            if key == "failures":
                failed = int(val)
            elif key == "errors":
                errors = int(val)
    if total == 0 and returncode != 0:
        errors = max(errors, 1)  # import error before any test ran
    passed = max(total - failed - errors, 0)
    ok = returncode == 0 and total > 0 and failed == 0 and errors == 0
    return {"total": total, "passed": passed, "failed": failed, "errors": errors, "ok": ok,
            "timed_out": False, "output_tail": text[-1500:]}


def grade(task, worktree):
    dest = Path(worktree) / HIDDEN_DIR
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(task.hidden_tests, dest)
    (dest / "__init__.py").touch()
    try:
        return run_unittest(worktree, HIDDEN_DIR, task.test_timeout_s)
    finally:
        shutil.rmtree(dest, ignore_errors=True)
