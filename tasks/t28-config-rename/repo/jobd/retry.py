"""Retry decisions."""
from . import job as jobs


def delay_for(settings, attempts):
    """Seconds to wait before retry number `attempts` (1 = first retry): doubles each time."""
    return settings.retry_backoff_s * (2 ** (attempts - 1))


def should_retry(settings, job):
    return job.attempts <= settings.retry_limit


def after_failure(settings, job, queue, dead_letters):
    """Requeue a failed job or give up on it. Returns "retry" or "dead"."""
    if should_retry(settings, job):
        jobs.transition(job, "queued")
        queue.push(job)
        return "retry"
    jobs.transition(job, "dead")
    dead_letters.add(job)
    return "dead"
