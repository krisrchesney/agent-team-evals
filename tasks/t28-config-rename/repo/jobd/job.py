"""Jobs: a name, a payload and where they are in their life."""
import itertools
from dataclasses import dataclass, field

from .errors import ValidationError

STATES = ("queued", "running", "done", "failed", "dead")
_ids = itertools.count(1)


@dataclass
class Job:
    handler: str
    payload: dict = field(default_factory=dict)
    priority: int = 5
    attempts: int = 0
    state: str = "queued"
    id: str = ""
    error: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"job_{next(_ids):06d}"


def create(handler, payload=None, priority=5, max_payload_kb=256):
    if not isinstance(handler, str) or not handler.strip():
        raise ValidationError("handler is required", field="handler")
    if not isinstance(priority, int) or not 0 <= priority <= 9:
        raise ValidationError("priority must be between 0 and 9", field="priority")
    payload = dict(payload or {})
    if len(repr(payload)) > max_payload_kb * 1024:
        raise ValidationError(f"payload is larger than {max_payload_kb} KB", field="payload")
    return Job(handler.strip(), payload, priority)


def transition(job, state):
    if state not in STATES:
        raise ValidationError(f"unknown state {state!r}", field="state")
    allowed = {
        "queued": {"running", "dead"},
        "running": {"done", "failed", "queued"},
        "failed": {"queued", "dead"},
        "done": set(),
        "dead": set(),
    }
    if state not in allowed[job.state]:
        raise ValidationError(f"a {job.state} job cannot become {state}", field="state")
    job.state = state
    return job
