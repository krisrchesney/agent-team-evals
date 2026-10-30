"""Run jobs in dependency order."""
from .actions import ACTIONS
from .graph import order
from .model import Result


def run(jobs, actions=None):
    """Run every job once, in dependency order. Returns a list of Results in that order."""
    actions = ACTIONS if actions is None else actions
    results = {}
    for job in order(jobs):
        blocked = next((d for d in job.deps if results[d].status != "ok"), None)
        if blocked is not None:
            reason = f"dependency '{blocked}' {results[blocked].status}"
            results[job.name] = Result(job.name, "skipped", reason=reason)
            continue
        fn = actions.get(job.action)
        if fn is None:
            results[job.name] = Result(job.name, "failed", error=f"unknown action '{job.action}'")
            continue
        try:
            output = fn(**job.args)
        except Exception as e:  # an action may raise anything
            results[job.name] = Result(job.name, "failed", error=str(e) or type(e).__name__)
        else:
            results[job.name] = Result(job.name, "ok", output=output)
    return [results[job.name] for job in order(jobs)]
