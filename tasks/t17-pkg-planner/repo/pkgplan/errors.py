"""Exception types shared by every pkgplan module."""


class PkgError(Exception):
    """Base class for all pkgplan errors."""


class VersionError(PkgError, ValueError):
    """A version string could not be parsed."""


class ConstraintError(PkgError, ValueError):
    """A constraint string could not be parsed."""


class LockError(PkgError, ValueError):
    """A lock file could not be parsed."""


class ResolutionError(PkgError):
    """Dependencies could not be resolved or ordered."""
