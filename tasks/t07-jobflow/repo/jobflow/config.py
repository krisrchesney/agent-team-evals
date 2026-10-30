"""Build Jobs from a parsed JSON spec: {"jobs": [{"name": ..., "action": ..., "deps": [...], "args": {...}}]}"""
from .graph import order
from .model import ConfigError, Job


def load_jobs(spec):
    if not isinstance(spec, dict) or not isinstance(spec.get("jobs"), list):
        raise ConfigError("spec must be an object with a 'jobs' list")
    jobs = []
    seen = set()
    for i, raw in enumerate(spec["jobs"]):
        name = raw.get("name") if isinstance(raw, dict) else None
        if not isinstance(name, str) or not name:
            raise ConfigError(f"job #{i + 1} needs a name")
        if name in seen:
            raise ConfigError(f"duplicate job '{name}'")
        seen.add(name)
        action = raw.get("action")
        if not isinstance(action, str) or not action:
            raise ConfigError(f"job '{name}' needs an action")
        deps = raw.get("deps", [])
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            raise ConfigError(f"job '{name}': deps must be a list of names")
        args = raw.get("args", {})
        if not isinstance(args, dict):
            raise ConfigError(f"job '{name}': args must be an object")
        jobs.append(Job(name, action, tuple(deps), dict(args)))
    for job in jobs:
        for dep in job.deps:
            if dep not in seen:
                raise ConfigError(f"job '{job.name}' depends on unknown job '{dep}'")
    order(jobs)  # raises on a cycle
    return jobs
