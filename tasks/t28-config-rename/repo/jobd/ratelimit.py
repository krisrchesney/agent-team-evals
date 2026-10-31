"""A token bucket for limiting how fast jobs of one handler start."""


class TokenBucket:
    def __init__(self, rate_per_s, burst, now=0.0):
        self.rate = float(rate_per_s)
        self.burst = float(burst)
        self.tokens = float(burst)
        self.stamp = now

    def _refill(self, now):
        elapsed = max(0.0, now - self.stamp)
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.stamp = now

    def take(self, now, n=1):
        self._refill(now)
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def wait_time(self, now, n=1):
        self._refill(now)
        missing = n - self.tokens
        return 0.0 if missing <= 0 else missing / self.rate
