"""datapipe: run dict records through a chain of stages.

    from datapipe import build_pipeline
    pipe = build_pipeline([
        {"type": "filter", "field": "amount", "op": "gt", "value": 0},
        {"type": "dedupe", "key": ["id"]},
    ])
    result = pipe.run(records)
    result.records, result.dead_letters, result.stats
"""
from .config import build_pipeline, build_stage
from .errors import ConfigError, PipelineError, StageError
from .pipeline import Pipeline

__all__ = ["build_pipeline", "build_stage", "Pipeline", "PipelineError", "ConfigError", "StageError"]
