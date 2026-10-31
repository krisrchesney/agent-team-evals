"""Text helpers for result pages."""
import re

_SPACE = re.compile(r"\s+")


def squeeze(text):
    return _SPACE.sub(" ", text).strip()


def truncate(text, width, ellipsis="..."):
    """Cut at a word boundary; the result, ellipsis included, is at most `width` characters."""
    text = squeeze(text)
    if len(text) <= width:
        return text
    cut = text[: max(0, width - len(ellipsis))]
    if " " in cut:
        cut = cut[: cut.rindex(" ")]
    return cut + ellipsis


def excerpt(text, term, width=80):
    """A window of `text` around the first occurrence of `term` (case-insensitive)."""
    text = squeeze(text)
    at = text.casefold().find(term.casefold())
    if at < 0:
        return truncate(text, width)
    start = max(0, at - width // 3)
    end = min(len(text), start + width)
    piece = text[start:end].strip()
    return ("..." if start > 0 else "") + piece + ("..." if end < len(text) else "")


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")
