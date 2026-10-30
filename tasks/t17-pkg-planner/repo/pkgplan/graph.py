"""Questions about the dependency graph of a whole registry."""
from .names import normalize


def reverse_dependencies(registry, name):
    """Display names of packages where any version depends on `name`, sorted by lookup key."""
    key = normalize(name)
    found = []
    for pkg in registry.names():
        if any(normalize(dep) == key for pv in registry.versions(pkg) for dep in pv.deps):
            found.append(pkg)
    return found


def reachable(registry, name):
    """Display names of every package reachable from any version of `name`, excluding `name` itself."""
    start = normalize(name)
    seen = {start}
    todo = [start]
    while todo:
        current = todo.pop()
        for pv in registry.versions(current):
            for dep in pv.deps:
                key = normalize(dep)
                if key not in seen and dep in registry:
                    seen.add(key)
                    todo.append(key)
    seen.discard(start)
    return [registry.display_name(key) for key in sorted(seen)]
