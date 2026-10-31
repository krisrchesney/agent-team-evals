class PatchError(Exception):
    """Base class of everything this package raises on purpose."""


class ParseError(PatchError):
    """The patch text is malformed. `line` is the 1-based line number in the patch text."""

    def __init__(self, message, line=None):
        super().__init__(message)
        self.line = line


class PatchFailed(PatchError):
    """Some hunks do not apply. `failed` lists their 1-based numbers in the file patch; `path` is set by
    the tree functions."""

    def __init__(self, message, failed, path=None):
        super().__init__(message)
        self.failed = list(failed)
        self.path = path


class MissingFile(PatchError):
    def __init__(self, path):
        super().__init__("no such file: %s" % path)
        self.path = path


class FileExists(PatchError):
    def __init__(self, path):
        super().__init__("file already exists: %s" % path)
        self.path = path


class UnsafePath(PatchError):
    def __init__(self, path):
        super().__init__("path escapes the root: %s" % path)
        self.path = path


class DuplicateTarget(PatchError):
    def __init__(self, path):
        super().__init__("two file patches for %s" % path)
        self.path = path
