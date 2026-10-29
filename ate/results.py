"""Results JSONL: one line per (task, config, repetition). Schema in docs/results.schema.json."""
import json
from pathlib import Path

from . import REPO_ROOT, SCHEMA_VERSION

SCHEMA_PATH = REPO_ROOT / "docs" / "results.schema.json"
STATUSES = ("passed", "failed", "budget_exceeded", "timeout", "agent_error", "rate_limited", "auth_error",
            "harness_error")

# Minimal stdlib validation: required keys and their JSON types. The full JSON Schema
# (docs/results.schema.json) documents the same contract for other tools.
_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool,
          "object": dict, "array": list, "null": type(None)}


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(record, schema=None):
    """Return a list of problems (empty = valid). Checks required keys, types, enums, one level deep."""
    schema = schema or load_schema()
    problems = []
    for key in schema["required"]:
        if key not in record:
            problems.append(f"missing {key}")
    for key, spec in schema["properties"].items():
        if key not in record:
            continue
        types = spec.get("type")
        types = types if isinstance(types, list) else [types]
        if types != [None] and not any(_is(record[key], t) for t in types):
            problems.append(f"{key} should be {types}, got {type(record[key]).__name__}")
        if "enum" in spec and record[key] not in spec["enum"]:
            problems.append(f"{key}={record[key]!r} not in {spec['enum']}")
        if spec.get("type") == "object" and isinstance(record[key], dict):
            for sub in spec.get("required", []):
                if sub not in record[key]:
                    problems.append(f"missing {key}.{sub}")
    if record.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version should be {SCHEMA_VERSION}")
    return problems


def _is(value, type_name):
    py = _TYPES.get(type_name)
    if py is None:
        return True
    if type_name in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, py)


def append(path, record):
    problems = validate(record)
    if problems:
        raise ValueError(f"result record invalid: {problems}")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def read(paths):
    out = []
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            out.extend(json.loads(line) for line in fh if line.strip())
    return out
