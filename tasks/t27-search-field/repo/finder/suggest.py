"""Spelling suggestions: "did you mean ...?" from the words already in the index."""
from .analysis.tokenizer import words

SUGGEST_FIELDS = ("title", "tags")


def edit_distance(a, b, limit=3):
    """Levenshtein distance, or limit + 1 as soon as it is clear it exceeds `limit`."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > limit:
            return limit + 1
        prev = cur
    return prev[-1]


def vocabulary(index):
    seen = set()
    for name in SUGGEST_FIELDS:
        seen.update(index.vocabulary(name))
    return sorted(seen)


def suggest_word(index, word, limit=3, max_distance=2):
    word = word.casefold()
    scored = []
    for candidate in vocabulary(index):
        if candidate == word:
            return []
        dist = edit_distance(word, candidate, max_distance)
        if dist <= max_distance:
            scored.append((dist, candidate))
    scored.sort()
    return [c for _, c in scored[:limit]]


def suggest_query(index, text):
    """The query with each unknown word replaced by its best guess, or None if nothing changed."""
    changed, out = False, []
    for word in words(text):
        options = suggest_word(index, word, limit=1)
        if options:
            out.append(options[0])
            changed = True
        else:
            out.append(word)
    return " ".join(out) if changed else None
