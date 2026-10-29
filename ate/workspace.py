"""Git isolation: one seed repo per task, one worktree per run.

The seed repo is a throwaway git repo holding the task's repo/ snapshot as a single commit.
Every run gets `git worktree add` on its own branch from that commit, so all runs of a task start
from byte-identical files and `git diff <seed>` is exactly what the agents changed.

Works with git 2.16 (no `git worktree remove`; we delete the folder and `git worktree prune`).
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

EXCLUDES = [".ate-stamp", "__pycache__/", "*.pyc", "_ate_hidden/", ".claude/", ".ate/"]
GIT_ID = ["-c", "user.name=ate", "-c", "user.email=ate@localhost", "-c", "core.autocrlf=false"]


def git(cwd, *args, env=None, check=True):
    proc = subprocess.run(["git", *GIT_ID, *args], cwd=cwd, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def ensure_seed(task, work_root):
    """Create (once) the seed repo for a task. Rebuild it if the snapshot changed."""
    seed = Path(work_root) / "seeds" / task.id
    stamp = _snapshot_stamp(task.repo)
    if (seed / ".git").exists() and (seed / ".ate-stamp").read_text() == stamp:
        return seed, git(seed, "rev-parse", "HEAD")
    if seed.exists():
        _rmtree(seed)
    shutil.copytree(task.repo, seed)
    git(seed, "init", "-q")
    # info/exclude is shared by every worktree, so these never show up in diffs or snapshots.
    exclude = seed / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("".join(f"{p}\n" for p in EXCLUDES))
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", f"seed {task.id}")
    (seed / ".ate-stamp").write_text(stamp)
    return seed, git(seed, "rev-parse", "HEAD")


def _snapshot_stamp(repo):
    parts = []
    for p in sorted(repo.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            st = p.stat()
            parts.append(f"{p.relative_to(repo).as_posix()}:{st.st_size}:{int(st.st_mtime)}")
    return "\n".join(parts)


def add_worktree(seed, seed_sha, path, branch):
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"worktree path already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    git(seed, "worktree", "add", "-b", branch, str(path), seed_sha)
    return path


def remove_worktree(seed, path):
    _rmtree(Path(path))
    git(seed, "worktree", "prune", check=False)


def snapshot_tree(worktree):
    """Tree id of the working directory (tracked + untracked), without touching the real index."""
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        git(worktree, "read-tree", "HEAD", env=env)
        git(worktree, "add", "-A", env=env)
        return git(worktree, "write-tree", env=env)


def restore_tree(worktree, tree):
    """Put the working directory back to `tree` (used when a read-only stage wrote files)."""
    current = snapshot_tree(worktree)
    added = git(worktree, "diff", "--name-only", "--diff-filter=A", tree, current).splitlines()
    for rel in added:
        target = Path(worktree) / rel
        if target.exists():
            target.unlink()
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        git(worktree, "read-tree", tree, env=env)
        git(worktree, "checkout-index", "-a", "-f", env=env)


def diff_stats(worktree, base_sha, tree):
    out = git(worktree, "diff", "--numstat", base_sha, tree)
    files = ins = dels = 0
    for line in out.splitlines():
        a, d, _ = line.split("\t", 2)
        files += 1
        ins += int(a) if a.isdigit() else 0
        dels += int(d) if d.isdigit() else 0
    return {"files": files, "insertions": ins, "deletions": dels}


def changed_paths(worktree, base_sha, tree):
    return git(worktree, "diff", "--name-only", base_sha, tree).splitlines()


def _rmtree(path):
    def onerror(func, p, _exc):
        os.chmod(p, 0o700)
        func(p)
    if path.exists():
        shutil.rmtree(path, onerror=onerror)
