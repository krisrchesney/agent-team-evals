"""State stores. A store maps (rule name, key) to a JSON-serialisable dict, and never shares the dicts
it holds with its callers (it copies on get and on set)."""
import copy
import json
import os

from .errors import StoreCorrupt


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

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                text = fh.read()
        except FileNotFoundError:
            return {}
        try:
            doc = json.loads(text)
        except ValueError as exc:
            raise StoreCorrupt("%s is not valid JSON" % self.path) from exc
        if not isinstance(doc, dict) or doc.get("version") != 1 or not isinstance(doc.get("rules"), dict):
            raise StoreCorrupt("%s has an unexpected layout" % self.path)
        return doc["rules"]

    def _save(self, rules):
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"version": 1, "rules": rules}, sort_keys=True))
        os.replace(tmp, self.path)

    def get(self, rule, key):
        return self._load().get(rule, {}).get(key)

    def set(self, rule, key, state):
        rules = self._load()
        rules.setdefault(rule, {})[key] = state
        self._save(rules)

    def delete(self, rule, key):
        rules = self._load()
        if key not in rules.get(rule, {}):
            return
        del rules[rule][key]
        if not rules[rule]:
            del rules[rule]
        self._save(rules)

    def delete_rule(self, rule):
        rules = self._load()
        if rule not in rules:
            return
        del rules[rule]
        self._save(rules)

    def keys(self, rule):
        return sorted(self._load().get(rule, {}))
