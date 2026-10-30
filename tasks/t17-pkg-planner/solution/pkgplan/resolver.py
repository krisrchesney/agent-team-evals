"""Greedy dependency resolution."""
import re
from collections import deque

from .constraint import Constraint
from .errors import ConstraintError, ResolutionError
from .names import normalize
from .version import Version

_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(.*)$")


def parse_requirement(text):
    """Split 'web>=2.0,<3' into ('web', Constraint('>=2.0,<3')). A missing constraint means '*'."""
    match = _REQUIREMENT.match(text)
    if match is None:
        raise ConstraintError(f"invalid requirement: {text!r}")
    name, rest = match.groups()
    return name, Constraint(rest.strip() or "*")


def resolve(registry, requirements, installed=None, upgrade=(), upgrade_all=False, prerelease=False):
    """Choose one version per package. Returns PackageVersions in the order they were chosen."""
    installed = {normalize(n): v if isinstance(v, Version) else Version(v) for n, v in (installed or {}).items()}
    upgrade = {normalize(n) for n in upgrade}
    seen = {}  # key -> [(Constraint, requirer display name), ...] in arrival order
    chosen = {}
    order = []
    queue = deque()

    def require(name, constraint, requirer):
        key = normalize(name)
        if name not in registry:
            raise ResolutionError(f"unknown package {name}")
        entries = seen.setdefault(key, [])
        entries.append((constraint, requirer))
        if key in chosen:
            pv = chosen[key]
            if not constraint.matches(pv.version):
                earlier = ",".join(str(c) for c, _ in entries[:-1])
                raise ResolutionError(
                    f"conflict on {pv.name}: {pv.version} was chosen for {earlier} "
                    f"but {constraint} is required by {requirer}")
        elif key not in queue:
            queue.append(key)

    def choose(key):
        constraints = [c for c, _ in seen[key]]
        candidates = registry.versions(key)
        if key in installed and key not in upgrade and not upgrade_all:
            current = registry.get(key, installed[key])
            # an installed version is kept whenever it satisfies the constraints, whatever its flags
            if current is not None and all(c.matches(current.version) for c in constraints):
                return current
        allow_pre = prerelease or any(c.has_prerelease_operand for c in constraints)
        for pv in candidates:
            if pv.version.is_prerelease and not allow_pre:
                continue
            if pv.yanked and not any(c.pins(pv.version) for c in constraints):
                continue
            if all(c.matches(pv.version) for c in constraints):
                return pv
        requirers = []
        for _, who in seen[key]:
            if who not in requirers:
                requirers.append(who)
        wanted = ",".join(str(c) for c in constraints)
        raise ResolutionError(
            f"no version of {registry.display_name(key)} satisfies {wanted} (required by {', '.join(requirers)})")

    for text in requirements:
        name, constraint = parse_requirement(text)
        require(name, constraint, "<root>")
    while queue:
        key = queue.popleft()
        pv = choose(key)
        chosen[key] = pv
        order.append(pv)
        for dep in sorted(pv.deps, key=normalize):
            require(dep, Constraint(pv.deps[dep]), pv.name)
    return order
