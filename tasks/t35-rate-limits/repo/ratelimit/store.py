"""State stores. A store maps (rule name, key) to a JSON-serialisable dict, and never shares the dicts
it holds with its callers (it copies on get and on set)."""
import copy


class MemoryStore:
    def __init__(self):
        self._data = {}

    def get(self, rule, key):
        state = self._data.get(rule, {}).get(key)
        return copy.deepcopy(state)

    def set(self, rule, key, state):
        self._data.setdefault(rule, {})[key] = copy.deepcopy(state)

    def delete(self, rule, key):
        self._data.get(rule, {}).pop(key, None)

    def delete_rule(self, rule):
        self._data.pop(rule, None)

    def keys(self, rule):
        return sorted(self._data.get(rule, {}))


class JsonFileStore:
    """Same interface as MemoryStore, persisted in one JSON file. See docs/SPEC.md."""

    def __init__(self, path):
        self.path = path

    def get(self, rule, key):
        raise NotImplementedError

    def set(self, rule, key, state):
        raise NotImplementedError

    def delete(self, rule, key):
        raise NotImplementedError

    def delete_rule(self, rule):
        raise NotImplementedError

    def keys(self, rule):
        raise NotImplementedError
