`confkit.settings.load(path)` reads an INI file over the built-in `DEFAULTS` and returns a nested
dict `{section: {key: value}}`. Let environment variables override it:

1. New signature `load(path=None, env=None)`. `path=None` means "no file, defaults only". `env` is a
   mapping of variable names to strings; `env=None` means use `os.environ`. Tests pass `env` in.
   Precedence, lowest to highest: `DEFAULTS`, then the file, then the environment. `load()` returns
   a fresh dict every time and never modifies `DEFAULTS`.
2. A variable is named `APP_<SECTION>__<KEY>`: the prefix `APP_`, the section name in upper case,
   two underscores, the key name in upper case. Example: `APP_DATABASE__POOL_SIZE` is
   `database.pool_size`. Names are matched exactly as written here (upper case only).
3. When `env` contains the variable for a key, its value replaces that key's value from the file
   or `DEFAULTS`. Only keys that exist in `DEFAULTS` can be overridden; any other `APP_...` variable
   (unknown section, unknown key, keys that only the file defines, wrong separator) is ignored.
4. Values from the file and from the environment are converted to the type of the key's default.
   `int` and `float` use `int()` / `float()` after stripping surrounding whitespace. `bool` accepts
   `1, true, yes, on` as `True` and `0, false, no, off` as `False`, case-insensitive, whitespace
   stripped; anything else is invalid. `str` values are used as given. File keys that are not in
   `DEFAULTS` stay as they are now: kept, as raw strings.
5. A value that cannot be converted raises `confkit.ConfigError` (it subclasses `ValueError`). The
   message must name where the value came from: the variable name (e.g. `APP_SERVER__PORT`) for an
   environment value, or `section.key` (e.g. `server.port`) for a file value.
6. An environment variable that is set to an empty string, or to whitespace only, counts as not
   set: the file or default value is kept and no error is raised.

Standard library only. Existing tests are in `tests/`.
