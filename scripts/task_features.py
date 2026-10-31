"""Measure every task's size and shape, so results can be charted against difficulty.

  python scripts/task_features.py            print a table
  python scripts/task_features.py --write    also write docs/task_features.json

No API calls. The numbers are counted from the task folders, never typed in by hand.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ate import tasks  # noqa: E402

_REQ = re.compile(r"^\s*\d+[.)]\s", re.M)  # "3. Rows are ..." numbered lists
_REQ_TAG = re.compile(r"\bR(\d+)\b")  # "(R1)" or "R1." inline tags in the long specs
_TEST = re.compile(r"^\s*def test_", re.M)
_DOC_SUFFIXES = {".md", ".txt", ".rst"}


def _lines(path):
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def _py(root):
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def features(task):
    prompt = task.prompt
    repo_py = _py(task.repo)
    sol_py = _py(task.solution)
    new_files = [p for p in sol_py if not (task.repo / p.relative_to(task.solution)).exists()]
    docs = [p for p in task.repo.rglob("*") if p.suffix in _DOC_SUFFIXES and p.is_file()]
    config_files = [p for p in task.repo.rglob("*") if p.suffix in {".json", ".toml", ".ini", ".yaml", ".yml"}
                    and p.is_file()]
    hidden = list(task.hidden_tests.rglob("test*.py"))
    return {
        "id": task.id,
        "category": task.meta.get("category"),
        "difficulty": task.meta.get("difficulty"),
        "prompt_words": len(prompt.split()),
        "prompt_requirements": max(len(_REQ.findall(prompt)), len(set(_REQ_TAG.findall(prompt)))),
        "repo_py_files": len(repo_py),
        "repo_py_lines": sum(map(_lines, repo_py)),
        "repo_doc_files": len(docs),
        "repo_doc_words": sum(len(p.read_text(encoding="utf-8", errors="replace").split()) for p in docs),
        "repo_config_files": len(config_files),
        "solution_files": len(sol_py),
        "solution_new_files": len(new_files),
        "solution_py_lines": sum(map(_lines, sol_py)),
        "hidden_tests": sum(len(_TEST.findall(p.read_text(encoding="utf-8"))) for p in hidden),
    }


def main(argv):
    rows = [features(tasks.load_task(t)) for t in tasks.list_tasks()]
    cols = ["id", "category", "prompt_words", "prompt_requirements", "repo_py_lines", "repo_doc_words",
            "solution_files", "solution_py_lines", "hidden_tests"]
    print("  ".join(f"{c:>{max(len(c), 6)}}" if c not in ("id", "category") else f"{c:<22}" for c in cols))
    for r in rows:
        print("  ".join(f"{str(r[c]):>{max(len(c), 6)}}" if c not in ("id", "category") else f"{str(r[c]):<22}"
                        for c in cols))
    if "--write" in argv:
        out = ROOT / "docs" / "task_features.json"
        out.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
