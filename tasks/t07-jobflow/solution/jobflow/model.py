"""Data shared by every module: jobs, results and the config error."""
from dataclasses import dataclass, field


class ConfigError(ValueError):
    """The job spec or the command line is wrong."""


@dataclass(frozen=True)
class Job:
    name: str
    action: str
    deps: tuple = ()
    args: dict = field(default_factory=dict)
    retries: int = 0
    backoff: float = 0.0
    allow_failure: bool = False
    when: str = "success"


@dataclass
class Result:
    name: str
    status: str  # "ok", "failed" or "skipped"
    output: object = None
    error: str = ""
    reason: str = ""
    attempts: int = 0
    stage: int = 0
