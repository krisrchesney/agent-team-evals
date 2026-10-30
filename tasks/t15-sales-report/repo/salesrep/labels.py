"""Group labels. Region and product names are tidied before they are compared."""
import re

_SPACES = re.compile(r"\s+")


def tidy(text):
    """Strip the ends and squeeze every run of whitespace inside to one space ('North   East' -> 'North East')."""
    return _SPACES.sub(" ", text.strip())


def label_key(text):
    """The case-insensitive key two labels are grouped by."""
    return tidy(text).lower()


def first_spelling(existing, candidate):
    """Groups keep the first spelling seen; this makes that rule explicit."""
    return existing if existing is not None else tidy(candidate)
