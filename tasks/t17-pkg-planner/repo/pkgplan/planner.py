"""Turn a resolution into an ordered list of install steps."""
from .names import normalize


class Step:
    def __init__(self, name, version, action, size, yanked):
        self.name = name
        self.version = version
        self.action = action
        self.size = size
        self.yanked = yanked

    @property
    def key(self):
        return normalize(self.name)

    def __repr__(self):
        return f"Step({self.name!r}, {str(self.version)!r}, {self.action!r})"


def build_plan(resolved):
    """Order the resolved packages so dependencies come first (depth-first, in resolution order)."""
    by_key = {normalize(pv.name): pv for pv in resolved}
    done = set()
    steps = []

    def visit(pv):
        key = normalize(pv.name)
        if key in done:
            return
        done.add(key)
        for dep in pv.deps:
            if normalize(dep) in by_key:
                visit(by_key[normalize(dep)])
        steps.append(Step(pv.name, pv.version, "install", pv.size, pv.yanked))

    for pv in resolved:
        visit(pv)
    return steps
