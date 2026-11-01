class Ids:
    def __init__(self):
        self._next = {}

    def new(self, prefix):
        n = self._next.get(prefix, 1)
        self._next[prefix] = n + 1
        return f"{prefix}_{n:04d}"
