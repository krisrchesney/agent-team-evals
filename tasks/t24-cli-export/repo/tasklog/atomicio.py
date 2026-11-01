import os
import tempfile


def write_text(path, text):
    """Write `path` in one step: a half-written file is never left behind. Raises OSError on failure."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".tasklog-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
