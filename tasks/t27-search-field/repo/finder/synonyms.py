"""Query-time synonyms: `car` also finds `auto`."""
from .analysis.tokenizer import words


class SynonymTable:
    def __init__(self):
        self._groups = []

    def add_group(self, *group):
        group = tuple(sorted({w.casefold() for w in group if w.strip()}))
        if len(group) < 2:
            raise ValueError("a synonym group needs at least two words")
        self._groups.append(group)

    def expand(self, word):
        word = word.casefold()
        out = {word}
        for group in self._groups:
            if word in group:
                out.update(group)
        return sorted(out)

    def expand_query(self, text):
        """`a b` becomes `(a OR a2) (b)`: each plain word is replaced by its group."""
        parts = []
        for word in words(text):
            options = self.expand(word)
            parts.append(options[0] if len(options) == 1 else "(" + " OR ".join(options) + ")")
        return " ".join(parts)

    def __len__(self):
        return len(self._groups)
