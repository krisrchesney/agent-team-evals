"""Package-name handling."""
import re

_SEPARATORS = re.compile(r"[-_.]+")


def normalize(name):
    """Lookup key for a package name: lowercase, with runs of '-', '_' and '.' collapsed to one '-'."""
    return _SEPARATORS.sub("-", name.strip()).lower()
