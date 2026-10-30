"""Versions of the form MAJOR.MINOR.PATCH[-prerelease][+build]."""
import re
from functools import total_ordering

from .errors import VersionError

_IDENT = r"[0-9A-Za-z-]+"
_TAIL = rf"(?:-({_IDENT}(?:\.{_IDENT})*))?(?:\+({_IDENT}(?:\.{_IDENT})*))?"
_FULL = re.compile(rf"^(\d+)\.(\d+)\.(\d+){_TAIL}$")
_PARTIAL = re.compile(rf"^(\d+)(?:\.(\d+))?(?:\.(\d+))?{_TAIL}$")


def _prerelease_key(prerelease):
    """Sort key for the prerelease part: any prerelease sorts below the plain release."""
    if prerelease is None:
        return (1, ())
    parts = []
    for ident in prerelease.split("."):
        # numeric identifiers compare as numbers and sort below alphanumeric ones
        parts.append((0, int(ident), "") if ident.isdigit() else (1, 0, ident))
    return (0, tuple(parts))


@total_ordering
class Version:
    """An immutable version. Build metadata is kept for display but ignored by ==, < and hash()."""

    def __init__(self, text):
        match = _FULL.match(text.strip()) if isinstance(text, str) else None
        if match is None:
            raise VersionError(f"invalid version: {text!r}")
        self._load(match.groups())

    def _load(self, groups):
        major, minor, patch, self.prerelease, self.build = groups
        self.major, self.minor, self.patch = int(major), int(minor), int(patch)
        self._key = (self.major, self.minor, self.patch, _prerelease_key(self.prerelease))

    @property
    def is_prerelease(self):
        return self.prerelease is not None

    def __eq__(self, other):
        return isinstance(other, Version) and self._key == other._key

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key < other._key

    def __hash__(self):
        return hash(self._key)

    def __str__(self):
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease is not None:
            text += f"-{self.prerelease}"
        if self.build is not None:
            text += f"+{self.build}"
        return text

    def __repr__(self):
        return f"Version({str(self)!r})"


def parse_partial(text):
    """Parse a version that may omit minor and patch. Returns (Version, number of parts given)."""
    match = _PARTIAL.match(text.strip())
    if match is None:
        raise VersionError(f"invalid version: {text!r}")
    major, minor, patch, prerelease, build = match.groups()
    given = 1 + (minor is not None) + (patch is not None)
    full = f"{major}.{minor or 0}.{patch or 0}"
    if prerelease is not None:
        full += f"-{prerelease}"
    if build is not None:
        full += f"+{build}"
    return Version(full), given
