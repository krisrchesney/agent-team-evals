"""Jobs that ran out of retries."""
from .errors import NotFound


class DeadLetters:
    def __init__(self):
        self._jobs = {}

    def add(self, job):
        self._jobs[job.id] = job

    def __len__(self):
        return len(self._jobs)

    def all(self):
        return list(self._jobs.values())

    def revive(self, job_id, queue):
        """Put a dead job back on the queue with a fresh attempt count."""
        try:
            job = self._jobs.pop(job_id)
        except KeyError:
            raise NotFound(f"no dead job {job_id!r}", field="id") from None
        job.state, job.attempts, job.error = "queued", 0, ""
        queue.push(job)
        return job

    def purge(self):
        n = len(self._jobs)
        self._jobs.clear()
        return n
