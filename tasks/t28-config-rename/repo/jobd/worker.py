"""A worker runs one job at a time. Here "running" is synchronous so the daemon is easy to test."""
from . import job as jobs


class Worker:
    def __init__(self, name):
        self.name = name
        self.job = None
        self._handler = None
        self.completed = 0

    @property
    def busy(self):
        return self.job is not None

    def start(self, job, handler):
        jobs.transition(job, "running")
        job.attempts += 1
        self.job, self._handler = job, handler

    def finish(self):
        """Run the handler now. Returns (job, ok)."""
        job, handler = self.job, self._handler
        self.job = self._handler = None
        try:
            handler(job.payload)
        except Exception as exc:  # a handler may raise anything
            job.error = f"{type(exc).__name__}: {exc}"
            jobs.transition(job, "failed")
            return job, False
        jobs.transition(job, "done")
        self.completed += 1
        return job, True
