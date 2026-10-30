"""A very simple circuit breaker."""
import time


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold, window, cooldown, clock=time.monotonic):
        self.failure_threshold = failure_threshold
        self.window = window  # not used yet
        self.cooldown = cooldown
        self._clock = clock
        self._failures = 0
        self._opened_at = None

    @property
    def state(self):
        if self._opened_at is not None and self._clock() - self._opened_at > self.cooldown:
            self._opened_at = None
            self._failures = 0
        return "closed" if self._opened_at is None else "open"

    def allow(self):
        return self.state == "closed"

    def record_failure(self):
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = self._clock()

    def record_success(self):
        self._failures = 0
