from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    flag: str
    on: bool
    reason: str

    def as_dict(self):
        return {"flag": self.flag, "on": self.on, "reason": self.reason}
