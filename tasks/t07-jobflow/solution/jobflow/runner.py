"""Run jobs in dependency order."""
import time

from .actions import ACTIONS
from .graph import order, stages
from .model import ConfigError, Result


def select(jobs, only):
    """The named jobs plus everything they depend on, in declaration order."""
    if only is None:
        return list(jobs)
    by_name = {j.name: j for j in jobs}
    keep, todo = set(), []
    for name in only:
        if name not in by_name:
            raise ConfigError(f"unknown job '{name}'")
        todo.append(name)
    while todo:
        name = todo.pop()
        if name not in keep:
            keep.add(name)
            todo.extend(by_name[name].deps)
    return [j for j in jobs if j.name in keep]


def skip_reason(job, results, by_name):
    """Why `job` must not run given its dependencies' results, or None if it should run."""
    if job.when == "always":
        return None
    if job.when == "failure":
        failed = any(results[d].status == "failed" for d in job.deps)
        return None if failed else "no dependency failed"
    for d in job.deps:
        status = results[d].status
        if status != "ok" and not (status == "failed" and by_name[d].allow_failure):
            return f"dependency '{d}' {status}"
    return None


def attempt(job, actions, sleep):
    fn = actions.get(job.action)
    if fn is None:
        return Result(job.name, "failed", error=f"unknown action '{job.action}'", attempts=1)
    tries = 1 + job.retries
    for n in range(1, tries + 1):
        if n > 1 and job.backoff:
            sleep(job.backoff * 2 ** (n - 2))
        try:
            output = fn(**job.args)
        except Exception as e:  # an action may raise anything
            error = str(e) or type(e).__name__
        else:
            return Result(job.name, "ok", output=output, attempts=n)
    return Result(job.name, "failed", error=error, attempts=tries)


def run(jobs, actions=None, sleep=time.sleep, only=None):
    """Run the selected jobs once each, in dependency order. Returns Results in that order."""
    actions = ACTIONS if actions is None else actions
    ordered = order(select(jobs, only))
    by_name = {j.name: j for j in ordered}
    stage = stages(ordered)
    results = {}
    for job in ordered:
        reason = skip_reason(job, results, by_name)
        if reason is None:
            result = attempt(job, actions, sleep)
        else:
            result = Result(job.name, "skipped", reason=reason)
        result.stage = stage[job.name]
        results[job.name] = result
    return [results[j.name] for j in ordered]
