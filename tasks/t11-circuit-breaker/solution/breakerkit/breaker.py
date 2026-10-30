"""A circuit breaker with a rolling failure window and half-open probing."""
import time

CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold, window, cooldown, half_open_successes=1, probe_limit=1,
                 expected=(Exception,), clock=time.monotonic):
        if type(failure_threshold) is not int or failure_threshold < 1:
            raise ValueError("failure_threshold must be an int >= 1")
        if window <= 0 or cooldown <= 0:
            raise ValueError("window and cooldown must be > 0")
        if type(half_open_successes) is not int or half_open_successes < 1:
            raise ValueError("half_open_successes must be an int >= 1")
        if type(probe_limit) is not int or probe_limit < half_open_successes:
            raise ValueError("probe_limit must be an int >= half_open_successes")
        self.failure_threshold = failure_threshold
        self.window = window
        self.cooldown = cooldown
        self.half_open_successes = half_open_successes
        self.probe_limit = probe_limit
        self.expected = expected
        self._clock = clock
        self._state = CLOSED
        self._failures = []  # timestamps of failures still inside the window
        self._opened_at = None
        self._probes = 0  # permits handed out in the current half-open period
        self._successes = 0  # successful probes in the current half-open period
        self._epoch = 0  # bumped on every transition
        self._transitions = []

    def _move(self, new_state, at):
        self._transitions.append((at, self._state, new_state))
        self._state = new_state
        self._epoch += 1
        self._failures = []
        self._probes = self._successes = 0
        self._opened_at = at if new_state == OPEN else None

    def _refresh(self):
        """The state is a function of the clock: cooldown ending moves OPEN to HALF_OPEN."""
        if self._state == OPEN and self._clock() - self._opened_at >= self.cooldown:
            self._move(HALF_OPEN, self._opened_at + self.cooldown)

    @property
    def state(self):
        self._refresh()
        return self._state

    @property
    def transitions(self):
        self._refresh()
        return list(self._transitions)

    def allow(self):
        self._refresh()
        if self._state == CLOSED:
            return True
        if self._state == HALF_OPEN and self._probes < self.probe_limit:
            self._probes += 1
            return True
        return False

    def record_failure(self):
        self._refresh()
        now = self._clock()
        if self._state == CLOSED:
            self._failures = [t for t in self._failures if now - t < self.window] + [now]
            if len(self._failures) >= self.failure_threshold:
                self._move(OPEN, now)
        elif self._state == HALF_OPEN:
            self._move(OPEN, now)

    def record_success(self):
        self._refresh()
        if self._state == CLOSED:
            self._failures = []
        elif self._state == HALF_OPEN:
            self._successes += 1
            if self._successes >= self.half_open_successes:
                self._move(CLOSED, self._clock())

    def retry_after(self):
        self._refresh()
        if self._state != OPEN:
            return 0.0
        return max(0.0, self.cooldown - (self._clock() - self._opened_at))

    def reset(self):
        self._refresh()
        if self._state != CLOSED:
            self._move(CLOSED, self._clock())
        self._failures = []

    def call(self, fn, *args, **kwargs):
        if not self.allow():
            raise CircuitOpenError("circuit is not accepting calls")
        probing, epoch = self._state == HALF_OPEN, self._epoch
        try:
            result = fn(*args, **kwargs)
        except self.expected:
            self.record_failure()
            raise
        except BaseException:
            if probing and self._state == HALF_OPEN and self._epoch == epoch:
                self._probes -= 1  # an unrelated error neither passes nor fails the probe
            raise
        self.record_success()
        return result
