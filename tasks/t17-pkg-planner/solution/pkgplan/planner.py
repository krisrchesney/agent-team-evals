"""Turn a resolution into an ordered list of install steps."""
import heapq

from .errors import ResolutionError
from .names import normalize
from .version import Version


class Step:
    def __init__(self, name, version, action, size, yanked):
        self.name = name
        self.version = version
        self.action = action  # install, upgrade, downgrade or keep
        self.size = size
        self.yanked = yanked

    @property
    def key(self):
        return normalize(self.name)

    def __repr__(self):
        return f"Step({self.name!r}, {str(self.version)!r}, {self.action!r})"


def _action(version, current):
    if current is None:
        return "install"
    if version == current:
        return "keep"
    return "upgrade" if version > current else "downgrade"


def build_plan(resolved, installed=None):
    """Order the resolved packages so dependencies come first.

    Among packages that are ready, the one with the smallest lookup key goes next.
    """
    installed = {normalize(n): v if isinstance(v, Version) else Version(v) for n, v in (installed or {}).items()}
    by_key = {normalize(pv.name): pv for pv in resolved}
    waiting = {key: {normalize(d) for d in pv.deps} - {key} for key, pv in by_key.items()}
    ready = [key for key, deps in waiting.items() if not deps]
    heapq.heapify(ready)
    steps = []
    while ready:
        key = heapq.heappop(ready)
        pv = by_key[key]
        steps.append(Step(pv.name, pv.version, _action(pv.version, installed.get(key)), pv.size, pv.yanked))
        del waiting[key]
        for other, deps in waiting.items():
            if key in deps:
                deps.discard(key)
                if not deps:
                    heapq.heappush(ready, other)
    if waiting:
        names = ", ".join(by_key[key].name for key in sorted(waiting))
        raise ResolutionError(f"dependency cycle among: {names}")
    return steps
