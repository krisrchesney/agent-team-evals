"""One command for "is the repo healthy": compile everything, run the harness tests,
validate every task, and do an oracle dry run. No API calls. Exit 0 = healthy."""
import compileall
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def step(name, cmd):
    print(f"== {name}")
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        print(f"FAILED: {name}")
        sys.exit(1)


def main():
    print("== compile")
    if not compileall.compile_dir(ROOT / "ate", quiet=1) or not compileall.compile_dir(ROOT / "tests", quiet=1):
        print("FAILED: compile")
        sys.exit(1)
    step("harness tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."])
    step("task validation", [sys.executable, "-m", "ate", "validate"])
    with tempfile.TemporaryDirectory() as tmp:
        step("oracle dry run", [sys.executable, "-m", "ate", "run", "--dry-run", "--oracle", "--reps", "1",
                                "--work-root", str(Path(tmp) / "work"), "--results-dir", str(Path(tmp) / "res")])
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
