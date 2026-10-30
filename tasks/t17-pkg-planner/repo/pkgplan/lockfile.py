"""Lock files: the versions a plan settled on, one 'name==version' per line."""
from .errors import LockError
from .names import normalize
from .version import Version


def dump_lock(steps):
    """Lock text for a plan, one line per step in plan order."""
    return "".join(f"{s.name}=={s.version}\n" for s in steps)


def load_lock(text):
    """Parse lock text into {lookup key: Version}."""
    locked = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        name, sep, version = raw.partition("==")
        if not sep:
            raise LockError(f"line {number}: expected name==version")
        locked[normalize(name)] = Version(version.strip())
    return locked
