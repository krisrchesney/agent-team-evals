"""Reading settings from environment variables named JOBD_<SETTING>."""
from .deprecations import RENAMED
from .schema import SETTINGS

PREFIX = "JOBD_"


def variable_for(name):
    return PREFIX + name.upper()


def read(environ):
    """Raw values from `environ`, keyed by setting name (old names included, if present)."""
    out = {}
    for name in list(SETTINGS) + list(RENAMED):
        var = variable_for(name)
        if var in environ:
            out[name] = environ[var]
    return out
