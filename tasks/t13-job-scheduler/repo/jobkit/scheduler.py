"""The scheduler: runs jobs one at a time, honouring priorities, retries and dependencies."""
import itertools

from .backoff import retry_delay
from .job import DONE, FAILED, PENDING, SKIPPED, WAITING, Job


class Scheduler:
    def __init__(self, clock, base_delay=1.0, max_delay=60.0):
        self.clock = clock
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.results = {}
        self.errors = {}
        self._jobs = {}
        self._seq = itertools.count()

    # ---- building the job set ------------------------------------------------------------

    def submit(self, job_id, fn, priority=0, deps=(), max_retries=0):
        if job_id in self._jobs:
            raise ValueError(f"duplicate job id {job_id!r}")
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be an int >= 0")
        self._jobs[job_id] = Job(job_id, fn, priority, deps, max_retries, next(self._seq))

    def _check_deps(self):
        for job in self._jobs.values():
            for dep in job.deps:
                if dep not in self._jobs:
                    raise KeyError(dep)
        state = {}  # id -> 1 while on the current path, 2 when fully explored

        def visit(job_id):
            if state.get(job_id) == 2:
                return
            if state.get(job_id) == 1:
                raise ValueError(f"dependency cycle through {job_id!r}")
            state[job_id] = 1
            for dep in self._jobs[job_id].deps:
                visit(dep)
            state[job_id] = 2

        for job_id in self._jobs:
            visit(job_id)

    # ---- running ---------------------------------------------------------------------------

    def run(self):
        self._check_deps()
        while True:
            runnable = [j for j in self._jobs.values()
                        if j.status in (PENDING, WAITING) and self._deps_done(j)]
            if not runnable:
                break
            job = min(runnable, key=Job.sort_key)
            wait = job.ready_at - self.clock.now()
            if wait > 0:
                self.clock.sleep(wait)
            self._attempt(job)
        return {job_id: job.status for job_id, job in self._jobs.items()}

    def _deps_done(self, job):
        return all(self._jobs[dep].status == DONE for dep in job.deps)

    def _attempt(self, job):
        started = self.clock.now()
        try:
            value = job.fn()
        except Exception as exc:
            self._fail(job, exc, started)
        else:
            job.status = DONE
            job.result = value
            self.results[job.id] = value

    def _fail(self, job, exc, now):
        job.error = exc
        job.failures += 1
        self._skip_dependents(job)
        if job.failures < job.max_retries:
            job.status = WAITING
            job.ready_at = now + retry_delay(job.failures, self.base_delay, self.max_delay)
            job.seq = next(self._seq)  # back of the queue
        else:
            job.status = FAILED
            self.errors[job.id] = exc

    def _skip_dependents(self, job):
        for other in self._jobs.values():
            if job.id in other.deps and other.status == PENDING:
                other.status = SKIPPED
