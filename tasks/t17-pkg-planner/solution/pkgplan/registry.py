"""An in-memory package index."""
from .names import normalize
from .version import Version


class PackageVersion:
    """One published version of one package."""

    def __init__(self, name, version, deps, size, yanked):
        self.name = name  # display name, as first registered
        self.version = version
        self.deps = deps  # dependency name -> constraint text
        self.size = size  # download size in bytes
        self.yanked = yanked

    def __repr__(self):
        return f"PackageVersion({self.name!r}, {str(self.version)!r})"


class Registry:
    def __init__(self):
        self._packages = {}  # normalized name -> {"name": display name, "versions": {Version: PackageVersion}}

    @classmethod
    def from_dict(cls, data):
        """Build from {"name": {"1.0.0": {"deps": {...}, "size": 10, "yanked": false}, ...}, ...}."""
        registry = cls()
        for name, versions in data.items():
            for text, meta in versions.items():
                registry.add(name, text, meta.get("deps"), meta.get("size", 0), meta.get("yanked", False))
        return registry

    def add(self, name, version, deps=None, size=0, yanked=False):
        if isinstance(version, str):
            version = Version(version)
        if type(size) is not int or size < 0:
            raise ValueError(f"size must be a non-negative int, got {size!r}")
        entry = self._packages.setdefault(normalize(name), {"name": name.strip(), "versions": {}})
        if version in entry["versions"]:
            raise ValueError(f"duplicate version {version} of {entry['name']}")
        entry["versions"][version] = PackageVersion(entry["name"], version, dict(deps or {}), size, bool(yanked))

    def __contains__(self, name):
        return normalize(name) in self._packages

    def display_name(self, name):
        return self._packages[normalize(name)]["name"]

    def names(self):
        """Display names, sorted by lookup key."""
        return [self._packages[key]["name"] for key in sorted(self._packages)]

    def versions(self, name):
        """All versions of a package, highest first."""
        entry = self._packages[normalize(name)]
        return [entry["versions"][v] for v in sorted(entry["versions"], reverse=True)]

    def get(self, name, version):
        entry = self._packages.get(normalize(name))
        return entry["versions"].get(version) if entry else None

    def search(self, prefix):
        """Display names whose lookup key starts with the prefix's lookup key (a prefix match, not substring)."""
        wanted = normalize(prefix)
        return [self._packages[key]["name"] for key in sorted(self._packages) if key.startswith(wanted)]
