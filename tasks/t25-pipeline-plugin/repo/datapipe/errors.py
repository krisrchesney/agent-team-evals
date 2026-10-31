class PipelineError(Exception):
    pass


class ConfigError(PipelineError):
    """A stage is set up wrongly. Raised while the pipeline is built, never while it runs."""

    def __init__(self, stage, message):
        super().__init__(f"stage {stage!r}: {message}")
        self.stage = stage
        self.message = message


class StageError(PipelineError):
    """A stage failed and the run stops. `index` is the record's position in that stage's input,
    or None if it failed while flushing."""

    def __init__(self, stage, index, cause):
        where = "while flushing" if index is None else f"on record {index}"
        super().__init__(f"stage {stage!r} failed {where}: {cause}")
        self.stage = stage
        self.index = index
        self.cause = cause


class Reject(Exception):
    """Raised by Stage.reject: this record is bad. It is not an error in the stage."""

    def __init__(self, record, reason):
        super().__init__(reason)
        self.record = record
        self.reason = reason
