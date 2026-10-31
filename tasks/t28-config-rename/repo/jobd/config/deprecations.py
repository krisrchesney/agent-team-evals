"""Settings that were renamed. The old name keeps working, with a warning.

How a rename is supported:
  * every source (file, environment, command line) may still give the old name; `apply_renames`
    turns it into the new name and warns once per old name per source;
  * if a source gives both names, the new name wins;
  * `Settings` still answers to the old name as an attribute (see settings.py);
  * the old name is documented in the "Renamed settings" table of docs/settings.md.
"""
import warnings

RENAMED = {
    "loglevel": "log_level",
}


class DeprecatedSettingWarning(DeprecationWarning):
    """A setting was given, or read, under a name that has been replaced."""


def message(old, new):
    return f"setting {old!r} is deprecated; use {new!r}"


def warn(old, new, stacklevel=3):
    warnings.warn(message(old, new), DeprecatedSettingWarning, stacklevel=stacklevel)


def apply_renames(raw, source):
    """Return `raw` with old names replaced by new ones. `source` is only used in messages."""
    out = {}
    pending = {}
    for name, value in raw.items():
        if name in RENAMED:
            warn(name, RENAMED[name])
            pending[RENAMED[name]] = value
        else:
            out[name] = value
    for new, value in pending.items():
        out.setdefault(new, value)
    return out
