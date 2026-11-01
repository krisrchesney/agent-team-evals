"""Saying no to new jobs when the queue is too full."""


class Backpressure:
    def __init__(self, settings):
        self.limit = settings.queue_size
        # Start warning when there are 50 waiting jobs for every worker.
        self.warn_depth = min(settings.worker_threads * 50, self.limit)

    def should_reject(self, depth):
        return depth >= self.limit

    def level(self, depth):
        if depth >= self.limit:
            return "reject"
        if depth >= self.warn_depth:
            return "warn"
        return "ok"
