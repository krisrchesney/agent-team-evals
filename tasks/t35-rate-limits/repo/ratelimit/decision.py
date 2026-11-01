import math
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Decision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: Optional[float]  # seconds until the same request would be allowed; None = never
    reset_after: float  # seconds until the limiter is back to its idle state

    def headers(self):
        out = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(math.ceil(self.reset_after)),
        }
        if not self.allowed and self.retry_after is not None:
            out["Retry-After"] = str(max(1, math.ceil(self.retry_after)))
        return out
