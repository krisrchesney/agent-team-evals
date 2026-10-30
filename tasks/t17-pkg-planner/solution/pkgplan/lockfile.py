"""Lock files: the versions a plan settled on, one 'name==version' per line."""
from .errors import LockError
from .names import normalize
from .version import Version

HEADER = "# pkgplan lock v1"


def dump_lock(steps):
    """Lock text for a plan: a header line, then every step sorted by lookup key."""
    lines = [HEADER] + [f"{s.name}=={s.version}" for s in sorted(steps, key=lambda s: s.key)]
    return "".join(line + "\n" for line in lines)


def load_lock(text):
    """Parse lock text into {lookup key: Version}. Blank lines and '#' comments are skipped."""
    locked = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, version = line.partition("==")
        if not sep or not name.strip():
            raise LockError(f"line {number}: expected name==version")
        key = normalize(name)
        if key in locked:
            raise LockError(f"line {number}: duplicate package {name.strip()}")
        locked[key] = Version(version.strip())
    return locked
