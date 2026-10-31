from dataclasses import dataclass

from .errors import ConfigError


@dataclass
class RunContext:
    run_number: int


@dataclass
class Result:
    records: list
    dead_letters: list
    stats: dict


class Pipeline:
    def __init__(self, stages):
        seen = set()
        for stage in stages:
            if stage.name in seen:
                raise ConfigError(stage.name, "two stages have this name")
            seen.add(stage.name)
        self.stages = list(stages)
        self.runs = 0

    def run(self, records):
        self.runs += 1
        context = RunContext(self.runs)
        dead, out, opened = [], [], []
        try:
            for stage in self.stages:
                stage.reset()
                stage.open(context)
                opened.append(stage)
            for record in records:
                self._feed(0, record, dead, out)
            for level, stage in enumerate(self.stages):
                for record in stage.run_flush():
                    self._feed(level + 1, record, dead, out)
        finally:
            for stage in reversed(opened):
                stage.close()
        return Result(out, dead, {s.name: dict(s.stats) for s in self.stages})

    def _feed(self, level, record, dead, out):
        if level == len(self.stages):
            out.append(record)
            return
        for produced in self.stages[level].handle(record, dead):
            self._feed(level + 1, produced, dead, out)
