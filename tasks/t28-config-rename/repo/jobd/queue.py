"""The job queue: highest priority first, oldest first within a priority."""
import heapq
import itertools

from .errors import Conflict


class JobQueue:
    def __init__(self, capacity=1000):
        self.capacity = capacity
        self._heap = []
        self._tick = itertools.count()
        self._jobs = {}

    def depth(self):
        return len(self._jobs)

    def push(self, job):
        if self.depth() >= self.capacity:
            raise Conflict("queue is full", field="queue")
        if job.id in self._jobs:
            raise Conflict(f"job {job.id} is already queued", field="id")
        self._jobs[job.id] = job
        heapq.heappush(self._heap, (-job.priority, next(self._tick), job.id))

    def pop(self):
        while self._heap:
            _, _, job_id = heapq.heappop(self._heap)
            job = self._jobs.pop(job_id, None)
            if job is not None:
                return job
        return None

    def cancel(self, job_id):
        return self._jobs.pop(job_id, None) is not None

    def peek_ids(self, limit=10):
        return [job_id for _, _, job_id in heapq.nsmallest(limit, self._heap) if job_id in self._jobs]
