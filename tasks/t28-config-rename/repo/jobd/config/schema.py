"""Every setting jobd knows: its type, default and allowed range. Order here is the order shown to users."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Setting:
    name: str
    kind: str          # "int", "float", "str" or "bool"
    default: object
    doc: str
    minimum: float = None
    maximum: float = None
    choices: tuple = None


SETTINGS = {s.name: s for s in [
    Setting("log_level", "str", "info", "Verbosity of the log.", choices=("debug", "info", "warning", "error")),
    Setting("queue_workers", "int", 4, "How many worker threads run jobs at the same time.", 1, 256),
    Setting("queue_size", "int", 1000, "Most jobs that may wait in the queue.", 1, 100000),
    Setting("retry_limit", "int", 3, "How many times a failed job is retried.", 0, 20),
    Setting("retry_backoff_s", "float", 1.5, "Seconds before the first retry; doubles each time.", 0, 600),
    Setting("poll_interval_s", "float", 0.5, "Seconds between looks at an empty queue.", 0.01, 60),
    Setting("metrics_port", "int", 9102, "Port for the metrics endpoint; 0 turns it off.", 0, 65535),
    Setting("shutdown_grace_s", "float", 30.0, "Seconds running jobs get to finish on shutdown.", 0, 3600),
    Setting("heartbeat_s", "float", 5.0, "Seconds between heartbeats to peers.", 0.5, 300),
    Setting("pool_name", "str", "default", "Name of this worker pool in logs and metrics."),
    Setting("max_payload_kb", "int", 256, "Largest accepted job payload, in kilobytes.", 1, 65536),
    Setting("job_timeout_s", "float", 300.0, "Seconds before a running job is cancelled.", 1, 86400),
]}


def names():
    return list(SETTINGS)


def defaults():
    return {s.name: s.default for s in SETTINGS.values()}
