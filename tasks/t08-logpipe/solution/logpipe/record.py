"""The record every stage of the pipeline passes along."""
from dataclasses import dataclass, field

LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")


@dataclass(frozen=True)
class Record:
    ts: int
    level: str
    msg: str
    fields: dict = field(default_factory=dict)
