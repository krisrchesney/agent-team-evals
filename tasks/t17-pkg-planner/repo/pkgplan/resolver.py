"""Greedy dependency resolution."""
import re
from collections import deque

from .constraint import Constraint
from .errors import ConstraintError, ResolutionError
from .names import normalize

_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(.*)$")


def parse_requirement(text):
    """Split 'web>=2.0.0,<3.0.0' into ('web', Constraint('>=2.0.0,<3.0.0')). A missing constraint means '*'."""
    match = _REQUIREMENT.match(text)
    if match is None:
        raise ConstraintError(f"invalid requirement: {text!r}")
    name, rest = match.groups()
    return name, Constraint(rest.strip() or "*")


def resolve(registry, requirements):
    """Choose one version per package. Returns PackageVersions in the order they were chosen."""
    seen = {}  # key -> [Constraint, ...] in arrival order
    chosen = {}
    order = []
    queue = deque()

    def require(name, constraint):
        key = normalize(name)
        if name not in registry:
            raise ResolutionError(f"unknown package {name}")
        seen.setdefault(key, []).append(constraint)
        if key not in chosen and key not in queue:
            queue.append(key)

    def choose(key):
        constraints = seen[key]
        for pv in registry.versions(key):
            if all(c.matches(pv.version) for c in constraints):
                return pv
        wanted = ",".join(str(c) for c in constraints)
        raise ResolutionError(f"no version of {registry.display_name(key)} satisfies {wanted}")

    for text in requirements:
        name, constraint = parse_requirement(text)
        require(name, constraint)
    while queue:
        key = queue.popleft()
        pv = choose(key)
        chosen[key] = pv
        order.append(pv)
        for dep, text in pv.deps.items():
            require(dep, Constraint(text))
    return order
