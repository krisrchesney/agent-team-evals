"""Canonical spellings that finance matches on."""
import re


def sku(text):
    """Upper case, with spaces, dashes, dots and slashes removed: " cv-10 220 " -> "CV10220"."""
    return re.sub(r"[\s\-./]", "", text).upper()


def text(value):
    """Collapse runs of whitespace to one space and strip the ends."""
    return " ".join(value.split())
