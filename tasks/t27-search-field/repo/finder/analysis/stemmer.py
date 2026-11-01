"""A small English suffix stripper. Good enough to match "running" with "runs"."""

_VOWELS = "aeiou"


def _has_vowel(word):
    return any(c in _VOWELS for c in word)


def _undouble(word):
    if len(word) > 2 and word[-1] == word[-2] and word[-1] not in "lsz" + _VOWELS:
        return word[:-1]
    return word


def stem(word):
    if len(word) <= 3 or not word.isalpha():
        return word
    if word.endswith("sses"):
        return word[:-2]
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    for suffix in ("ing", "ed"):
        if word.endswith(suffix) and _has_vowel(word[: -len(suffix)]) and len(word) - len(suffix) >= 3:
            return _undouble(word[: -len(suffix)])
    if word.endswith("es") and len(word) > 4 and word[-3] in "sxz":
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word
