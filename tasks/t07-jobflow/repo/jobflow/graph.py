"""Dependency ordering."""
from .model import ConfigError


class CycleError(ConfigError):
    pass


def order(jobs):
    """Jobs in a valid run order. Among jobs that are ready, the one declared first goes first."""
    pending = list(jobs)
    done = set()
    out = []
    while pending:
        for job in pending:
            if all(d in done for d in job.deps):
                break
        else:
            names = ", ".join(sorted(j.name for j in pending))
            raise CycleError(f"dependency cycle involving: {names}")
        pending.remove(job)
        done.add(job.name)
        out.append(job)
    return out
