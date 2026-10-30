"""Operation registry. See docs/CONVENTIONS.md before adding an operation."""
import importlib

OPERATIONS = {}

# Modules whose operations are registered. A module that is not listed here is never imported.
MODULES = ["charges"]


def operation(name, *, scope):
    def register(fn):
        if name in OPERATIONS:
            raise RuntimeError(f"operation {name} registered twice")
        OPERATIONS[name] = (fn, scope)
        return fn
    return register


def load():
    for module in MODULES:
        importlib.import_module(f"{__name__}.{module}")
